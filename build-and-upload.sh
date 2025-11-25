#!/bin/bash

# Build and Upload Script for Internship Matcher
# Builds the frontend locally and uploads to EC2 via SCP

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# =====================================
# Configuration
# =====================================
EC2_USER="ubuntu"  # or ec2-user for Amazon Linux
EC2_HOST="internshipmatcher.com"  # or use: ec2-3-149-255-34.us-east-2.compute.amazonaws.com
EC2_KEY="~/.ssh/ec2-keys/key1.pem"
EC2_PATH="~/Internship-App"

# =====================================
# Parse command line arguments
# =====================================
while [[ $# -gt 0 ]]; do
  case $1 in
    --host)
      EC2_HOST="$2"
      shift 2
      ;;
    --user)
      EC2_USER="$2"
      shift 2
      ;;
    --key)
      EC2_KEY="$2"
      shift 2
      ;;
    --path)
      EC2_PATH="$2"
      shift 2
      ;;
    --help)
      echo "Usage: ./build-and-upload.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --host HOST    EC2 hostname or IP address"
      echo "  --user USER    SSH user (default: ubuntu)"
      echo "  --key PATH     Path to SSH private key"
      echo "  --path PATH    Remote path to app (default: ~/Internship-App)"
      echo "  --help         Show this help message"
      echo ""
      echo "Example:"
      echo "  ./build-and-upload.sh --key ~/.ssh/my-key.pem"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# =====================================
# Validate Configuration
# =====================================
if [ -z "$EC2_HOST" ]; then
    echo -e "${RED}❌ Error: EC2 host not specified!${NC}"
    echo "Edit the EC2_HOST variable in this script or use --host argument"
    exit 1
fi

# Build SSH options
SSH_OPTS=""
if [ -n "$EC2_KEY" ]; then
    # Expand tilde in EC2_KEY path
    EC2_KEY="${EC2_KEY/#\~/$HOME}"

    if [ ! -f "$EC2_KEY" ]; then
        echo -e "${RED}❌ Error: SSH key not found: $EC2_KEY${NC}"
        exit 1
    fi
    SSH_OPTS="-i $EC2_KEY"
fi

echo "🚀 Building and uploading frontend to EC2..."
echo ""
echo "Configuration:"
echo "  Host: $EC2_HOST"
echo "  User: $EC2_USER"
echo "  Path: $EC2_PATH"
if [ -n "$EC2_KEY" ]; then
    echo "  Key:  $EC2_KEY"
fi
echo ""

# =====================================
# 1. Check Frontend Environment
# =====================================
echo -e "${YELLOW}📋 Step 1: Checking frontend environment...${NC}"

if [ ! -f "frontend/.env" ]; then
    echo -e "${RED}❌ Error: frontend/.env not found!${NC}"
    echo "Creating .env from template..."
    cat > frontend/.env << 'EOF'
REACT_APP_STACK_AUTH_PROJECT_ID=6d1393dc-a806-42e0-9986-c4a6c5b1a287
REACT_APP_STACK_AUTH_PUBLISHABLE_CLIENT_KEY=pck_70amzm1w07k1mcstxe3f3vync419yq1w520yedh48kjc0
EOF
    echo -e "${GREEN}✅ Created frontend/.env${NC}"
fi

echo -e "${GREEN}✅ Environment file exists${NC}"

# =====================================
# 2. Build Frontend
# =====================================
echo -e "${YELLOW}📋 Step 2: Building React frontend for production...${NC}"

cd frontend

# Clean previous build
if [ -d "build" ]; then
    echo "Cleaning previous build..."
    rm -rf build
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm ci
fi

# Build
echo "Building frontend (this may take a minute)..."
npm run build

if [ ! -d "build" ]; then
    echo -e "${RED}❌ Error: Build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Frontend built successfully${NC}"

cd ..

# =====================================
# 3. Upload Build to EC2
# =====================================
echo -e "${YELLOW}📋 Step 3: Uploading build to EC2...${NC}"

# Create remote directory if it doesn't exist
echo "Creating remote directory..."
ssh $SSH_OPTS $EC2_USER@$EC2_HOST "mkdir -p $EC2_PATH/frontend"

# Upload build directory
echo "Uploading files (this may take a minute)..."
scp $SSH_OPTS -r frontend/build $EC2_USER@$EC2_HOST:$EC2_PATH/frontend/

echo -e "${GREEN}✅ Files uploaded successfully${NC}"

# =====================================
# 4. Trigger Deployment on EC2
# =====================================
echo -e "${YELLOW}📋 Step 4: Triggering deployment on EC2...${NC}"

read -p "Run deployment script on EC2? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ssh $SSH_OPTS -t $EC2_USER@$EC2_HOST "cd $EC2_PATH && ./deploy.sh"
else
    echo -e "${YELLOW}⚠️  Skipping deployment${NC}"
    echo ""
    echo "To deploy manually, SSH into your EC2 instance and run:"
    echo "  ssh $SSH_OPTS $EC2_USER@$EC2_HOST"
    echo "  cd $EC2_PATH"
    echo "  ./deploy.sh"
fi

# =====================================
# Complete
# =====================================
echo ""
echo "========================================"
echo -e "${GREEN}🎉 Build and Upload Complete!${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. If you didn't run deploy.sh, SSH to EC2 and run it:"
echo "     ssh $SSH_OPTS $EC2_USER@$EC2_HOST"
echo "     cd $EC2_PATH && ./deploy.sh"
echo ""
echo "  2. Visit your site:"
echo "     https://internshipmatcher.com"
echo ""