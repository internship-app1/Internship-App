# Production Deployment Fix - 404 API Errors

## Problem
Getting 404 errors in production because requests are hitting `http://localhost:8000/api/match-stream` instead of using the nginx proxy.

## Root Cause
The frontend `.env` file had `NODE_ENV=production` which interferes with Create React App's automatic environment detection during build.

## Solution

### On Your EC2 Instance

1. **Update the frontend `.env` file:**
```bash
cd ~/Internship-App/frontend
cat > .env << 'EOF'
REACT_APP_STACK_AUTH_PROJECT_ID=6d1393dc-a806-42e0-9986-c4a6c5b1a287
REACT_APP_STACK_AUTH_PUBLISHABLE_CLIENT_KEY=pck_70amzm1w07k1mcstxe3f3vync419yq1w520yedh48kjc0
EOF
```

2. **Rebuild the frontend:**
```bash
cd ~/Internship-App
./deploy.sh
```

**OR** manually rebuild:
```bash
cd ~/Internship-App/frontend
npm run build
cd ..
docker-compose restart nginx
```

## How It Works

### Development (local machine)
- `setupProxy.js` proxies `/api` → `http://localhost:8000`
- Used only by `react-scripts start`

### Production (EC2)
- `setupProxy.js` is **ignored** (only works in dev mode)
- Frontend makes requests to `/api/match-stream` (relative URL)
- Nginx proxies `/api/*` → `http://backend:8000/api/*`
- No need for `setupProxy.js` in production

## Environment Variables Explained

### `.env` (for local development)
```bash
REACT_APP_STACK_AUTH_PROJECT_ID=your-project-id
REACT_APP_STACK_AUTH_PUBLISHABLE_CLIENT_KEY=your-key
# REACT_APP_API_URL not needed - setupProxy.js handles it
```

### `.env.production` (for EC2 deployment)
```bash
REACT_APP_STACK_AUTH_PROJECT_ID=your-project-id
REACT_APP_STACK_AUTH_PUBLISHABLE_CLIENT_KEY=your-key
REACT_APP_API_URL=
# Empty = use relative URLs, nginx will proxy
```

## Verification

After deploying, check:

1. **Frontend build has correct settings:**
```bash
# On EC2
docker exec -it internship-nginx cat /usr/share/nginx/html/index.html | grep -o 'REACT_APP'
```

2. **Test API endpoint:**
```bash
curl -I https://internshipmatcher.com/api/cache-status
# Should return 200 OK
```

3. **Check browser network tab:**
- Requests should go to `https://internshipmatcher.com/api/match-stream`
- NOT `http://localhost:8000/api/match-stream`

## Key Points

✅ **DO:**
- Use empty `REACT_APP_API_URL` for relative URLs
- Let `npm run build` set `NODE_ENV=production` automatically
- Use nginx to proxy `/api` requests to backend

❌ **DON'T:**
- Put `NODE_ENV=production` in `.env` file
- Use `setupProxy.js` configuration for production
- Set full URLs in `REACT_APP_API_URL` (unless frontend/backend are on different domains)

## Troubleshooting

If still getting 404:

1. **Clear browser cache:**
```javascript
// In browser console
localStorage.clear();
sessionStorage.clear();
location.reload(true);
```

2. **Check nginx logs:**
```bash
docker logs internship-nginx --tail 100
```

3. **Verify backend is accessible:**
```bash
docker exec -it internship-nginx curl http://backend:8000/api/cache-status
```

4. **Rebuild with no cache:**
```bash
cd frontend
rm -rf node_modules/.cache
rm -rf build
npm run build
```