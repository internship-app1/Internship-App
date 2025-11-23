# Internship Matcher

An intelligent web application that scrapes internship opportunities from major tech companies and matches them with your resume using advanced AI-powered analysis. The system provides detailed compatibility scores, skill analysis, and personalized career insights.

---

## Table of Contents

- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation Steps](#installation-steps)
  - [Verification](#verification)
  - [Common Issues](#common-issues)
  - [Development vs Production](#development-vs-production)
  - [Deployment](#deployment)
  - [Project Structure](#project-structure)
- [How the Application Works](#how-the-application-works)
- [Matching: Deep Thinking Enabled](#matching-deep-thinking-enabled)
- [Matching: Deep Thinking Disabled](#matching-deep-thinking-disabled)
- [Skill Extraction Implementation Details](#skill-extraction-implementation-details)
- [Technical Stack](#technical-stack)
- [API Endpoints](#api-endpoints)
- [Job Scraping](#job-scraping)
- [Key Features](#key-features)
- [Testing](#testing)

---

## Quick Start

### Prerequisites

- **Python 3.8+** installed on your system
- **Node.js 14+** and npm for the React frontend
- **PostgreSQL** database (local or remote)
- **Redis** (optional but recommended for caching)
- **AWS Account** with S3 access for resume storage
- **OpenAI API Key** for AI-powered matching (required for "Think Deeper" mode)

### Installation Steps

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd Internship-App
   ```

2. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   This will install all required packages including:
   - FastAPI (web framework)
   - OpenAI (AI analysis)
   - pdfplumber (PDF parsing)
   - boto3 (AWS S3)
   - psycopg2 (PostgreSQL)
   - redis (caching)
   - playwright (web scraping)

3. **Set Up Environment Variables**

   Copy the template file:
   ```bash
   cp env_template.txt .env
   ```

   Edit `.env` and fill in your credentials:
   ```bash
   # Required - OpenAI API Key (get from https://platform.openai.com/api-keys)
   OPENAI_API_KEY=sk-your-openai-api-key-here

   # Required - AWS S3 Configuration
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=your-internship-app-bucket

   # Required - PostgreSQL Database
   DATABASE_URL=postgresql://username:password@localhost:5432/internship_db

   # Optional - Redis (improves performance)
   REDIS_URL=redis://localhost:6379

   # Required - Session Security
   SECRET_KEY=your-random-secret-key-here

   # Optional - Environment
   ENVIRONMENT=development
   ```

4. **Set Up PostgreSQL Database**

   Create a new database:
   ```bash
   # Using psql command line
   psql -U postgres
   CREATE DATABASE internship_db;
   \q
   ```

   Initialize the database tables:
   ```bash
   python job_database.py
   ```

   This creates the `jobs` table for caching internship opportunities.

5. **Set Up AWS S3 Bucket**

   - Log into AWS Console
   - Create a new S3 bucket (e.g., `my-internship-app-resumes`)
   - Configure bucket permissions for read/write access
   - Update `S3_BUCKET_NAME` in your `.env` file

6. **Install Playwright Browsers** (for web scraping)
   ```bash
   playwright install chromium
   ```

7. **Install Frontend Dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

8. **Start the Backend Server**
   ```bash
   python app.py
   ```

   The backend API will be available at `http://localhost:8000`

   You should see:
   ```
   🚀 Starting up Internship Matcher [DEVELOPMENT] with Hybrid Cache System...
   ✅ Startup complete!
   INFO:     Uvicorn running on http://0.0.0.0:8000
   ```

9. **Start the Frontend** (in a new terminal)
   ```bash
   cd frontend
   npm start
   ```

   The React app will open at `http://localhost:3001`

10. **Access the Application**

    Open your browser and navigate to `http://localhost:3001`

### Verification

Test that everything is working:

1. **Check backend health:**
   ```bash
   curl http://localhost:8000/api/cache-status
   ```

2. **Upload a sample resume** through the web interface

3. **Toggle "Think Deeper"** to test both matching modes

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'openai'`
- **Solution**: Run `pip install -r requirements.txt` again

**Issue**: `psycopg2.OperationalError: could not connect to server`
- **Solution**: Ensure PostgreSQL is running and `DATABASE_URL` is correct

**Issue**: `OpenAI API key not configured properly`
- **Solution**: Check that `OPENAI_API_KEY` in `.env` is valid

**Issue**: `S3 upload failed`
- **Solution**: Verify AWS credentials and bucket name in `.env`

**Issue**: Redis connection failed
- **Solution**: This is optional. App will work without Redis, but slower

### Development vs Production

**Development Mode** (default):
- Cache refreshes every 6 hours automatically
- Detailed debug logging
- CORS enabled for localhost
- Environment variable: `ENVIRONMENT=development`

**Production Mode**:
- Cache only refreshes when empty or manually triggered
- Minimal logging
- Configure CORS for your production frontend URL
- Environment variable: `ENVIRONMENT=production`

To run in production mode:
```bash
# In .env file
ENVIRONMENT=production

# Add your production frontend URL to CORS in app.py
# Example: "https://your-frontend.vercel.app"
```

### Deployment

For production deployment:

1. **Backend (Render, Railway, AWS EC2, etc.)**
   ```bash
   # Set environment variables on your platform
   # Start command:
   python app.py
   # or with gunicorn:
   gunicorn app:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
   ```

2. **Frontend (Vercel, Netlify, etc.)**
   ```bash
   cd frontend
   npm run build
   # Deploy the 'build' folder
   # Update API_URL to point to your backend
   ```

3. **Database (Railway, ElephantSQL, etc.)**
   - Create PostgreSQL instance
   - Update `DATABASE_URL` in environment variables

4. **Redis (Upstash, Redis Cloud, etc.)**
   - Create Redis instance
   - Update `REDIS_URL` in environment variables

### Project Structure

```
Internship-App/
├── app.py                          # Main FastAPI application
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (create from template)
├── env_template.txt               # Environment variables template
│
├── resume_parser/                 # Resume parsing module
│   ├── __init__.py
│   └── parse_resume.py           # PDF/image text extraction & skill extraction
│
├── matching/                      # Job matching logic
│   ├── __init__.py
│   ├── matcher.py                # Main matching algorithms (3-stage pipeline)
│   ├── llm_skill_extractor.py   # LLM-based skill extraction & matching
│   ├── metadata_matcher.py       # Experience level & metadata matching
│   └── main_workflow.py          # Example workflow (reference)
│
├── job_scrapers/                  # Web scraping modules
│   ├── __init__.py
│   ├── dispatcher.py             # Orchestrates all scrapers
│   ├── scrape_github_internships.py  # Pitt CSC repository scraper
│   ├── scrape_google.py          # Google Careers API
│   ├── scrape_meta.py            # Meta Careers (Playwright)
│   ├── scrape_microsoft.py       # Microsoft Careers API
│   └── scrape_salesforce.py      # Salesforce Careers API
│
├── job_cache.py                   # Hybrid Redis + PostgreSQL caching
├── job_database.py                # PostgreSQL database operations
├── s3_service.py                  # AWS S3 file storage
│
├── templates/                     # HTML templates (if using)
│   └── dashboard.html
│
├── static/                        # Static files (CSS, JS, images)
│
└── frontend/                      # React frontend
    ├── package.json
    ├── src/
    │   ├── App.js                # Main React component
    │   ├── components/           # React components
    │   └── ...
    └── public/
```

**Key Files**:
- `app.py` - FastAPI routes, startup logic, streaming endpoints
- `resume_parser/parse_resume.py` - Skill extraction (LLM vs text-based)
- `matching/matcher.py` - 3-stage matching pipeline
- `matching/llm_skill_extractor.py` - Dynamic skill matching
- `job_scrapers/dispatcher.py` - Parallel job scraping
- `job_cache.py` - Hybrid caching system

---

## How the Application Works

### High-Level Architecture

```
User Upload Resume → Resume Parsing → Skill Extraction → Job Scraping → Intelligent Matching → Ranked Results
```

### Step-by-Step Flow

1. **Resume Upload** (`app.py:569-676`)
   - User uploads resume (PDF, PNG, JPG, or JPEG) via the React frontend
   - File is uploaded to AWS S3 for secure storage (`s3_service.py`)
   - File is then downloaded from S3 for processing

2. **Resume Parsing & Skill Extraction** (`resume_parser/parse_resume.py`)
   - Text is extracted from PDF using `pdfplumber` or from images using `pytesseract`
   - **Two parsing modes available** (controlled by `think_deeper` checkbox):
     - **Deep Thinking Mode** (LLM-based): Uses GPT-5 Mini for intelligent skill extraction
     - **Quick Mode** (Text-based): Uses keyword matching for faster results

3. **Job Scraping** (`job_scrapers/dispatcher.py`)
   - Scrapes internship opportunities from major companies:
     - GitHub (via Pitt CSC repository)
     - Google Careers
     - Meta Careers
     - Microsoft Careers
     - Salesforce Careers
   - Jobs are cached in Redis + PostgreSQL hybrid system for performance
   - Automatic daily refresh to keep opportunities current

4. **Intelligent Matching** (`matching/matcher.py`)
   - **3-Stage Efficient Matching Pipeline**:
     - **Stage 1**: Intelligent Pre-filtering (narrows 1000s → 50 top candidates)
     - **Stage 2**: Batch LLM Analysis (single API call for all jobs)
     - **Stage 3**: Enhanced Results with rich descriptions
   - Jobs are scored 0-100 based on multiple factors
   - Results include detailed AI reasoning and skill gap analysis

5. **Results Display**
   - Jobs ranked by match score (highest first)
   - Each job includes:
     - Match score (0-100)
     - AI-generated reasoning
     - Matching skills vs. skills to develop
     - Experience level compatibility
     - Location and company details

---

## Matching: Deep Thinking Enabled

When the **"Think Deeper"** checkbox is **checked**, the application uses advanced LLM-based analysis for maximum accuracy.

### Skill Extraction (Deep Thinking)

**Location**: `resume_parser/parse_resume.py:164-190`

**Process**:
1. `parse_resume()` is called with `use_llm=True` (line 125)
2. Invokes `extract_skills_with_llm_full()` (line 168)
3. Uses **GPT-5 Mini** model via OpenAI API (line 246-252)
4. Sends comprehensive prompt that instructs the LLM to:
   - Extract ONLY skills the person actually possesses
   - Ignore skills in negative contexts ("I want to learn React" → NOT extracted)
   - Standardize skill names ("JS" → "JavaScript", "ML" → "Machine Learning")
   - Assess experience level (student/entry/experienced)
   - Determine years of experience and student status

**Output**:
```json
{
  "skills": ["Python", "JavaScript", "React", "SQL", "Git"],
  "experience_level": "student",
  "years_of_experience": 0,
  "is_student": true,
  "confidence_notes": "Strong technical portfolio with web development focus"
}
```

### Job Matching (Deep Thinking)

**Location**: `matching/matcher.py:1151-1200`

**3-Stage Process**:

#### Stage 1: Intelligent Pre-filtering (Lines 1170-1176)
- `intelligent_prefilter_jobs()` analyzes all scraped jobs
- Filters out inappropriate roles (senior positions for juniors, high experience requirements)
- Uses multi-factor scoring:
  - Skills in job title (15 points per match)
  - Skills in description (5 points per match)
  - Domain alignment (8 points per domain)
  - Company quality indicators (10 points for FAANG)
  - Remote/location preferences (3-5 points)
- Selects **top 50 candidates** from 1000s of jobs

#### Stage 2: Batch LLM Analysis (Lines 1178-1180)
- `batch_analyze_jobs_with_llm()` analyzes all 50 jobs in a **single API call**
- Uses **GPT-5** with comprehensive career advisor prompt (lines 829-930)
- **Weighted Scoring System** (total 100 points):
  - **Project Depth & Real-World Impact (35%)**: Production deployments, user impact, technical complexity
  - **Work Experience Quality (25%)**: Real internships/jobs, leadership, open source
  - **Skill Alignment (20%)**: Demonstrated skills matching the role
  - **Experience Level Appropriateness (15%)**: Role suitability for candidate's level
  - **Career Trajectory (5%)**: Growth potential and career fit
- Returns comprehensive analysis with scores, reasoning, skill matches, and red flags

#### Stage 3: Enhanced Results (Lines 1187-1189)
- `enhance_batch_results()` merges LLM analysis with original job data
- Creates rich, personalized descriptions for each job
- Includes AI reasoning, skill gaps, and career insights

### Cost & Performance (Deep Thinking)
- **Single LLM call** for 50 jobs (~$0.08-0.15 per analysis)
- **vs.** Old approach: 50 individual calls (~$1.00+)
- **83-85% cost reduction** while improving quality

---

## Matching: Deep Thinking Disabled

When the **"Think Deeper"** checkbox is **NOT checked**, the application uses faster text-based analysis.

### Skill Extraction (Quick Mode)

**Location**: `resume_parser/parse_resume.py:209-234`

**Process**:
1. `parse_resume()` is called with `use_llm=False` (line 125)
2. Invokes `extract_basic_skills_from_text()` (line 214)
3. **No LLM used** - Pure keyword matching approach
4. Searches for predefined technical skills using regex word boundaries (lines 97-115)

**Predefined Skills List** (line 97-105):
```python
basic_skill_keywords = [
    "Python", "Java", "JavaScript", "TypeScript", "React", "Angular", "Vue",
    "HTML", "CSS", "SQL", "Git", "Node.js", "Express", "Django", "Flask",
    "Spring", "AWS", "Azure", "GCP", "Docker", "Kubernetes", "MongoDB",
    "PostgreSQL", "MySQL", "TensorFlow", "PyTorch", "Pandas", "NumPy",
    "Machine Learning", "Data Analysis", "Software Engineering", "Programming",
    "C++", "C#", "PHP", "Ruby", "Go", "Rust", "Bootstrap", "jQuery",
    "REST API", "GraphQL", "Linux", "Testing", "Agile", "Scrum"
]
```

**Algorithm** (lines 110-114):
```python
for skill in basic_skill_keywords:
    skill_lower = skill.lower()
    # Word boundary regex ensures "Java" matches "Java developer" but not "JavaScript"
    if re.search(r'\b' + re.escape(skill_lower) + r'\b', text_lower):
        found_skills.append(skill)
```

**Fallback** (line 217-219):
- If basic extraction returns no skills, tries `extract_skills_with_regex()` with more comprehensive pattern matching

**Output**:
```python
["Python", "JavaScript", "React", "SQL", "Git", "AWS"]
# Simple list of matched skills - no metadata
```

### Job Matching (Quick Mode)

**Location**: `matching/matcher.py:1270-1320`

**Process**:
1. Uses `match_resume_to_jobs_legacy()` function (line 1270)
2. **Stage 1**: Same intelligent pre-filtering as deep thinking mode (lines 1288-1296)
   - Filters inappropriate roles
   - Selects top 50 candidates
3. **Stage 2**: Rule-based matching for each job (lines 1301-1307)
   - `match_job_to_resume()` analyzes job-resume compatibility (line 1304)
   - Uses dynamic skill matching with threshold (line 181)
   - Calculates score based on:
     - Number of matching skills / total required skills × 100
     - Bonuses for 3+ matches (+10) or 2+ matches (+5)
     - Differentiation factors (specific job titles, remote positions, description quality)
   - Combines with metadata scoring (experience level, location fit)
4. **Results**: Jobs sorted by score with detailed descriptions

### Performance (Quick Mode)
- **Much faster**: No API calls during skill extraction
- **Still intelligent**: Uses same pre-filtering and basic matching logic
- **Trade-off**: Less context-aware than deep thinking mode
- **Best for**: Quick scans or when API quotas are limited

---

## Skill Extraction Implementation Details

### Specifically: Where Does Skill Extraction Happen When Deep Thinking is NOT Checked?

**File**: `resume_parser/parse_resume.py`

**Function Call Stack**:
```
app.py:676
  ↓
parse_resume(downloaded_content, original_filename, use_llm=False)
  ↓ (line 209-234)
extract_basic_skills_from_text(text)  ← PRIMARY METHOD
  ↓ (if no skills found, line 217-219)
extract_skills_with_regex(text)       ← FALLBACK METHOD
```

**Detailed Breakdown**:

1. **Entry Point** (`app.py:676`)
   ```python
   resume_skills, resume_text, resume_metadata = parse_resume(
       downloaded_content,
       original_filename,
       use_llm=False  # ← Deep thinking disabled
   )
   ```

2. **Parse Resume Logic** (`parse_resume.py:125-238`)
   - Line 163: Checks `if use_llm:` condition
   - Line 209: **Else branch executes** (text-based mode)
   - Line 214: Calls `extract_basic_skills_from_text(text)`

3. **Basic Text Extraction** (`parse_resume.py:91-116`)
   - Line 97-105: Defines `basic_skill_keywords` list (40+ common technical skills)
   - Line 110-114: Loops through each skill and uses regex to find matches
   - Line 112-113: Uses word boundary regex `\b{skill}\b` to avoid partial matches
   - Line 115: Returns deduplicated list of found skills

4. **Fallback Regex** (`parse_resume.py:118-123`)
   - If basic extraction returns empty list
   - Line 219: Calls `extract_skills_with_regex(text)`
   - Line 122: Uses complex regex pattern with 100+ skill keywords
   - Includes programming languages, frameworks, tools, domains, soft skills

5. **Metadata Creation** (`parse_resume.py:226-231`)
   ```python
   metadata = {
       "experience_level": "student",  # Default assumption
       "years_of_experience": 0,
       "is_student": True,
       "confidence_notes": "Extracted using legacy text-based parsing"
   }
   ```

### Key Differences: Deep Thinking vs. Quick Mode

| Aspect | Deep Thinking Enabled | Deep Thinking Disabled |
|--------|----------------------|----------------------|
| **Skill Extraction** | GPT-5 Mini LLM analysis | Keyword regex matching |
| **Context Awareness** | Yes - understands "want to learn" vs "have" | No - any mention is extracted |
| **Standardization** | Automatic ("JS" → "JavaScript") | Manual (predefined list) |
| **Experience Analysis** | AI-assessed from resume content | Default "student" assumption |
| **Matching Method** | Batch LLM career fit analysis | Rule-based skill overlap scoring |
| **Cost** | ~$0.08-0.15 per analysis | Free (no API calls) |
| **Speed** | ~5-8 seconds | ~1-2 seconds |
| **Accuracy** | High - considers context & complexity | Moderate - keyword matching only |

---

## Technical Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React.js
- **AI Models**:
  - GPT-5 (job matching & career analysis)
  - GPT-5 Mini (resume skill extraction)
- **Caching**: Redis + PostgreSQL hybrid system
- **Storage**: AWS S3 (resume files)
- **Scraping**:
  - Playwright (dynamic sites)
  - BeautifulSoup (static sites)
  - Requests (API-based scraping)

---

## API Endpoints

### Main Endpoints

- `POST /api/match-stream` - Stream matching progress with real-time updates
- `POST /api/match` - Match resume to jobs (JSON response)
- `GET /api/cache-status` - Check job cache status
- `POST /api/refresh-cache` - Manually refresh job cache
- `GET /api/database-stats` - Database statistics

### Admin Endpoints

- `POST /api/refresh-cache?force_full=true` - Force full job refresh
- `POST /api/refresh-cache-incremental` - Incremental update only

---

## Job Scraping

### Supported Companies

1. **GitHub Internships** (`scrape_github_internships.py`)
   - Source: Pitt CSC Internship Repository
   - Method: GitHub API + JSON parsing
   - Frequency: Daily updates

2. **Google** (`scrape_google.py`)
   - Source: Google Careers API
   - Method: REST API with filters
   - Filter: Internship roles only

3. **Meta** (`scrape_meta.py`)
   - Source: Meta Careers portal
   - Method: Playwright dynamic scraping
   - Filter: Internship & university roles

4. **Microsoft** (`scrape_microsoft.py`)
   - Source: Microsoft Careers API
   - Method: REST API with pagination
   - Filter: Intern and university positions

5. **Salesforce** (`scrape_salesforce.py`)
   - Source: Salesforce Careers API
   - Method: REST API
   - Filter: Intern roles

### Cache System

**Hybrid Redis + PostgreSQL**:
- **Redis**: Fast in-memory cache (6-hour TTL)
- **PostgreSQL**: Persistent storage with job deduplication
- **Smart Refresh**: Auto-detects incremental vs. full updates
- **Daily Schedule**: Automatic refresh every 24 hours
- **On-Demand**: Manual refresh via API endpoint

**Benefits**:
- 10x faster job retrieval (from Redis)
- No duplicate jobs (PostgreSQL deduplication)
- Automatic stale job removal (30-day filter)
- Resilient to Redis failures (DB fallback)

---

## Key Features

### Resume Analysis
- Multi-format support (PDF, PNG, JPG, JPEG)
- OCR for image-based resumes
- Context-aware skill extraction (deep thinking mode)
- Experience level assessment
- Student status detection

### Intelligent Matching
- Multi-factor scoring algorithm
- Experience level compatibility checking
- Career trajectory analysis
- Real-world impact assessment
- Skill gap identification

### User Experience
- Real-time streaming progress updates
- Detailed AI-generated explanations
- Skill match breakdowns
- Location and company filters
- Responsive design

### Performance Optimizations
- Batch LLM processing (83% cost reduction)
- Intelligent pre-filtering (1000s → 50 jobs)
- Hybrid caching system (10x faster retrieval)
- S3 storage with automatic cleanup
- Parallel job scraping

---

## Testing

### Test Skill Extraction
```bash
python test_llm_skill_extraction.py
```

### Test Job Matching
```bash
curl http://localhost:8000/api/test-matching
```

### Test Cache System
```bash
curl http://localhost:8000/api/cache-status
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License.

---

## Support

For issues, questions, or feature requests, please open an issue on GitHub.
