import os
import re
import secrets
import subprocess
from pathlib import Path

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, File, UploadFile, HTTPException, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sse_starlette.sse import EventSourceResponse
import uvicorn
from dotenv import load_dotenv
import io
import json
import asyncio
from datetime import datetime

# Import our modules
from resume_parser import parse_resume, is_valid_resume
from job_scrapers.dispatcher import scrape_jobs
from matching.matcher import match_resume_to_jobs
from matching.metadata_matcher import extract_resume_metadata
import job_cache
from s3_service import upload_resume_to_s3, download_resume_from_s3, delete_resume_from_s3
from resume_tailor.tailor_resume import tailor_resume as _tailor_resume
from job_database import get_resume_cache, set_resume_cache

# Base directory of this file (used for templates/static/uploads paths)
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown with a proper lifespan context."""
    # ---- startup ----
    environment = os.getenv("ENVIRONMENT", "development").lower()
    print(f"🚀 Starting up Internship Matcher [{environment.upper()}] with Hybrid Cache System...")

    cache_available = job_cache.init_redis()

    if cache_available:
        cache_info = job_cache.get_cache_info()
        cached_jobs = job_cache.get_cached_jobs()
        should_refresh = False

        if environment == "development":
            if cached_jobs:
                db_info = cache_info.get('database', {})
                last_update = db_info.get('last_update')
                if last_update:
                    from datetime import datetime, timedelta
                    try:
                        last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                        time_since_update = datetime.now(last_update_time.tzinfo) - last_update_time
                        if time_since_update > timedelta(hours=6):
                            print(f"🔄 Cache is {time_since_update.total_seconds() / 3600:.1f} hours old - refreshing...")
                            should_refresh = True
                        else:
                            print(f"📦 Using existing cache: {len(cached_jobs)} jobs (updated {time_since_update.total_seconds() / 3600:.1f} hours ago)")
                    except Exception as e:
                        print(f"⚠️ Error parsing cache timestamp: {e}")
                else:
                    print(f"📦 Using existing cache: {len(cached_jobs)} jobs available")
            else:
                should_refresh = True
                print("📥 No cached jobs found - initializing cache...")
        else:
            if cached_jobs:
                print(f"📦 Using existing cache: {len(cached_jobs)} jobs available")
                print(f"🔍 Cache status: {cache_info.get('hybrid', {}).get('message', 'Unknown')}")
            else:
                should_refresh = True
                print("📥 No cached jobs found - initializing cache...")

        if should_refresh:
            try:
                jobs = await scrape_jobs(max_days_old=30)
                if jobs:
                    cache_result = job_cache.set_cached_jobs(jobs, cache_type='startup')
                    if cache_result.get('database_success') or cache_result.get('redis_success'):
                        print(f"✅ Startup cache initialized: {cache_result.get('new_jobs', 0)} new jobs, {len(jobs)} total")
                    else:
                        print("⚠️ Cache initialization failed")
                else:
                    print("⚠️ No jobs scraped on startup")
            except Exception as e:
                print(f"❌ Error during startup scraping: {e}")
    else:
        print("❌ Hybrid cache system unavailable - jobs will be scraped per request")

    try:
        final_info = job_cache.get_cache_info()
        if final_info.get('database', {}).get('status') == 'active':
            db_info = final_info['database']
            print(f"📊 Database: {db_info.get('active_jobs', 0)} active jobs")
        if final_info.get('redis', {}).get('status') == 'active':
            redis_info = final_info['redis']
            print(f"⚡ Redis: {redis_info.get('job_count', 0)} jobs cached")
    except Exception as e:
        print(f"⚠️ Error getting final cache status: {e}")

    print("✅ Startup complete!")

    # Start background refresh task and track it for clean cancellation
    refresh_task = asyncio.create_task(daily_cache_refresh_task())
    print("🕒 Daily cache refresh scheduler started")

    yield  # server is running

    # ---- shutdown ----
    refresh_task.cancel()
    try:
        await refresh_task
    except asyncio.CancelledError:
        pass


# Create FastAPI app
app = FastAPI(title="Internship Matcher", version="1.0.0", lifespan=lifespan)

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://internshipmatcher.com",
        "http://www.internshipmatcher.com",
        "https://internshipmatcher.com",
        "https://www.internshipmatcher.com",
        "http://3.149.255.34",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],  # Domain, EC2, and local dev

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Important for SSE streaming
)

# Add session middleware for basic session support
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "your-secret-key-here"))

# Setup templates and static files using absolute paths
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Create upload folder if it doesn't exist (absolute path)
UPLOAD_FOLDER = BASE_DIR / "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



async def daily_cache_refresh_task():
    """
    Background task that automatically refreshes the cache every 24 hours.
    This ensures jobs stay fresh without manual intervention.

    IMPROVED: Better error handling, logging, and recovery
    """
    refresh_count = 0

    while True:
        try:
            # Wait 24 hours before first refresh (cache was just initialized on startup)
            print(f"⏰ [Scheduled] Next cache refresh in 24 hours...")
            await asyncio.sleep(24 * 60 * 60)  # 24 hours in seconds

            refresh_count += 1
            print(f"🔄 [Scheduled #{refresh_count}] Starting daily cache refresh at {datetime.utcnow().isoformat()}")

            # Perform smart scraping with 30-day filter
            try:
                jobs = await scrape_jobs(max_days_old=30)
            except Exception as scrape_error:
                print(f"❌ [Scheduled] Scraping failed: {scrape_error}")
                import traceback
                traceback.print_exc()
                continue  # Don't stop the task, try again in 24h

            if jobs:
                # Store in hybrid cache system
                try:
                    cache_result = job_cache.set_cached_jobs(jobs, cache_type='daily_scheduled')
                    new_jobs = cache_result.get('new_jobs', 0)
                    total_jobs = cache_result.get('total_jobs', len(jobs))

                    if cache_result.get('database_success') or cache_result.get('redis_success'):
                        print(f"✅ [Scheduled #{refresh_count}] Daily refresh complete: {new_jobs} new jobs, {total_jobs} total active jobs")
                    else:
                        print(f"⚠️ [Scheduled #{refresh_count}] Cache refresh failed - no storage backend succeeded")
                except Exception as cache_error:
                    print(f"❌ [Scheduled #{refresh_count}] Cache storage failed: {cache_error}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"📝 [Scheduled #{refresh_count}] No new jobs found in daily refresh")

        except asyncio.CancelledError:
            print(f"🛑 Daily cache refresh task cancelled after {refresh_count} refreshes")
            break
        except Exception as e:
            print(f"❌ [Scheduled #{refresh_count}] Unexpected error in daily cache refresh: {e}")
            import traceback
            traceback.print_exc()
            # Continue running even if one refresh fails
            print(f"🔄 [Scheduled] Will retry in 24 hours...")
            continue


async def get_jobs_with_cache():
    """
    Get jobs using hybrid cache system (Redis + Database).
    This function is used by all endpoints to get job data efficiently.
    """
    # Try to get from hybrid cache system
    cached_jobs = job_cache.get_cached_jobs()
    
    if cached_jobs:
        print(f"⚡ Using {len(cached_jobs)} jobs from hybrid cache")
        return cached_jobs
    
    # Cache miss - use smart scraping strategy
    print("🌐 Cache miss - using smart scraping strategy...")
    try:
        # Smart scraping automatically detects incremental vs full
        # Default to 30-day filter to only get recent jobs
        jobs = await scrape_jobs(max_days_old=30)
        
        # Store in hybrid cache system
        if jobs:
            cache_result = job_cache.set_cached_jobs(jobs, cache_type='on_demand')
            new_jobs = cache_result.get('new_jobs', 0)
            total_jobs = cache_result.get('total_jobs', len(jobs))
            
            if cache_result.get('database_success') or cache_result.get('redis_success'):
                print(f"✅ Scraped and cached: {new_jobs} new jobs, {total_jobs} total")
            else:
                print(f"⚠️ Scraping successful but caching failed: {total_jobs} jobs")
            
            # Return all active jobs from cache for consistency
            return job_cache.get_cached_jobs() or jobs
        else:
            print("⚠️ No jobs scraped")
            return []
            
    except Exception as e:
        print(f"❌ Error during smart scraping: {e}")
        # Try to get any available jobs from database as fallback
        try:
            from job_cache import get_jobs_for_matching
            fallback_jobs = get_jobs_for_matching()
            if fallback_jobs:
                print(f"🔄 Using {len(fallback_jobs)} fallback jobs from database")
                return fallback_jobs
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
        
        return []


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home page - redirects to dashboard"""
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard - main page for resume upload"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "results": None,
        "error": None
    })


@app.post("/match", response_class=HTMLResponse)
async def match_resume(request: Request, resume: UploadFile = File(...)):
    """Match resume to internship opportunities"""
    try:
        # Validate file
        if not resume:
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "results": None,
                "error": "No file was uploaded. Please select a resume file."
            })

        # Check file extension
        file_extension = resume.filename.split('.')[-1].lower() if resume.filename else ''
        allowed_extensions = ['pdf', 'png', 'jpg', 'jpeg']
        
        if file_extension not in allowed_extensions:
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "results": None,
                "error": f"Invalid file type '{file_extension}'. Please upload a PDF, PNG, JPG, or JPEG file."
            })

        # Read file content
        try:
            file_content = await resume.read()
            if not file_content:
                return templates.TemplateResponse("dashboard.html", {
                    "request": request,
                    "results": None,
                    "error": "The uploaded file appears to be empty. Please upload a valid resume file."
                })
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "results": None,
                "error": f"Error reading the uploaded file: {str(e)}"
            })

        print(f"📥 Uploaded: {resume.filename}")
        print(f"📊 File size: {len(file_content)} bytes")
        print(f"🔍 File type: {resume.content_type}")

        # Parse resume using LLM (returns skills, text, and metadata)
        try:
            resume_skills, resume_text, resume_metadata = parse_resume(file_content, resume.filename)
            if not resume_skills:
                return templates.TemplateResponse("dashboard.html", {
                    "request": request,
                    "results": None,
                    "error": "No skills were detected in your resume. Please make sure your resume includes technical skills, programming languages, or relevant experience."
                })
        except Exception as e:
            print(f"❌ Error parsing resume: {e}")
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "results": None,
                "error": f"Error parsing your resume: {str(e)}"
            })

        print(f"🔍 Extracted resume skills: {resume_skills}")
        print(f"📊 Resume analysis: {resume_metadata.get('experience_level', 'unknown')} level")
        
        # Validate resume content
        if resume_text and not is_valid_resume(resume_text):
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "results": None,
                "error": "The uploaded file does not appear to be a valid resume. Please upload a document that contains relevant professional information."
            })

        # Get jobs from cache or scrape
        try:
            print("🌐 Fetching internship opportunities...")
            jobs = await get_jobs_with_cache()
            if not jobs:
                return templates.TemplateResponse("dashboard.html", {
                    "request": request,
                    "results": None,
                    "error": "Unable to fetch internship opportunities at this time. Please try again later."
                })
            print(f"📋 Total jobs available: {len(jobs)}")
        except Exception as e:
            print(f"❌ Error fetching jobs: {e}")
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "results": None,
                "error": f"Error fetching internship opportunities: {str(e)}"
            })

        # Match resume to jobs
        try:
            print("🎯 Starting job matching...")
            matched_jobs = match_resume_to_jobs(resume_skills, jobs, resume_text)
            if not matched_jobs:
                return templates.TemplateResponse("dashboard.html", {
                    "request": request,
                    "results": None,
                    "error": "No matching internship opportunities were found for your skills. Consider updating your resume with more relevant technical skills."
                })
            print(f"✅ Final matched jobs: {len(matched_jobs)}")
        except Exception as e:
            print(f"❌ Error matching jobs: {e}")
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "results": None,
                "error": f"Error matching your resume to jobs: {str(e)}"
            })

        # Return results
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "results": matched_jobs,
            "user": None
        })

    except Exception as e:
        print(f"❌ Unexpected error in match_resume: {e}")
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "results": None,
            "error": f"An unexpected error occurred: {str(e)}. Please try again or contact support if the problem persists."
        })


@app.post("/api/match")
async def api_match_resume(resume: UploadFile = File(...), think_deeper: str = Form("true")):
    """API endpoint for React frontend - returns JSON instead of HTML"""
    try:
        # Validate file
        if not resume:
            raise HTTPException(status_code=400, detail="No file was uploaded. Please select a resume file.")

        # Check file extension
        file_extension = resume.filename.split('.')[-1].lower() if resume.filename else ''
        allowed_extensions = ['pdf', 'png', 'jpg', 'jpeg']
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type '{file_extension}'. Please upload a PDF, PNG, JPG, or JPEG file."
            )

        # Read file content
        try:
            file_content = await resume.read()
            if not file_content:
                raise HTTPException(status_code=400, detail="The uploaded file appears to be empty. Please upload a valid resume file.")
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            raise HTTPException(status_code=400, detail=f"Error reading the uploaded file: {str(e)}")

        print(f"📥 Uploaded: {resume.filename}")
        print(f"📊 File size: {len(file_content)} bytes")
        print(f"🔍 File type: {resume.content_type}")

        # Upload file to S3
        s3_key = None
        try:
            print("☁️ Uploading resume to S3...")
            s3_key = upload_resume_to_s3(file_content, resume.filename)
            print(f"✅ Resume uploaded to S3: {s3_key}")
        except Exception as e:
            print(f"❌ S3 upload failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to upload resume: {str(e)}")

        # Download file from S3 for processing
        try:
            print("📥 Downloading resume from S3 for processing...")
            downloaded_content, original_filename = download_resume_from_s3(s3_key)
            print(f"✅ Downloaded {len(downloaded_content)} bytes from S3")
        except Exception as e:
            print(f"❌ S3 download failed: {e}")
            # Clean up S3 file if download fails
            if s3_key:
                delete_resume_from_s3(s3_key)
            raise HTTPException(status_code=500, detail=f"Failed to process resume: {str(e)}")

        # Parse resume using selected method (returns skills, text, and metadata)
        try:
            use_llm = think_deeper.lower() == "true"
            if use_llm:
                print("📄 Step 1/4: Analyzing your resume with AI (GPT-5)...")
            else:
                print("📄 Step 1/4: Analyzing your resume with text-based parsing...")
            resume_skills, resume_text, resume_metadata = parse_resume(downloaded_content, original_filename, use_llm)
            if not resume_skills:
                raise HTTPException(
                    status_code=400, 
                    detail="No skills were detected in your resume. Please make sure your resume includes technical skills, programming languages, or relevant experience."
                )
        except Exception as e:
            print(f"❌ Error parsing resume: {e}")
            raise HTTPException(status_code=400, detail=f"Error parsing your resume: {str(e)}")

        print(f"✅ Step 1 complete: Extracted {len(resume_skills)} skills from resume")
        print(f"🔍 Skills found: {resume_skills}")
        print(f"📊 Candidate level: {resume_metadata.get('experience_level', 'unknown')}")
        
        # Validate resume content
        if resume_text and not is_valid_resume(resume_text):
            raise HTTPException(
                status_code=400, 
                detail="The uploaded file does not appear to be a valid resume. Please upload a document that contains relevant professional information."
            )

        # Get jobs from cache or scrape
        try:
            print("🌐 Step 2/4: Fetching internship opportunities...")
            jobs = await get_jobs_with_cache()
            if not jobs:
                raise HTTPException(
                    status_code=500, 
                    detail="Unable to fetch internship opportunities at this time. Please try again later."
                )
            print(f"✅ Step 2 complete: Found {len(jobs)} internship opportunities")
        except Exception as e:
            print(f"❌ Error fetching jobs: {e}")
            raise HTTPException(status_code=500, detail=f"Error fetching internship opportunities: {str(e)}")

        # Match resume to jobs with intelligent prefiltering
        try:
            print("🤖 Step 3/4: Analyzing job requirements with AI...")
            print(f"🔍 Your skills: {resume_skills}")
            print(f"📊 Intelligent prefiltering will select top 50 jobs from {len(jobs)} total jobs based on your skills")
            
            # Pass ALL jobs - intelligent_prefilter_jobs will filter from 1000s → 50 based on THIS resume's skills
            print("🎯 Step 4/4: Matching your skills to job requirements...")
            matched_jobs = match_resume_to_jobs(resume_skills, jobs, resume_text, use_llm=use_llm)
            
            print(f"✅ Matching complete: Found {len(matched_jobs)} relevant opportunities")
            
            # Filter jobs with score > 0 for the final response
            jobs_with_matches = [job for job in matched_jobs if job.get('match_score', 0) > 0]
            
            if not jobs_with_matches:
                # Show all jobs with their scores for debugging
                print("❌ No jobs with score > 0 - showing all job scores for debugging:")
                for i, job in enumerate(matched_jobs[:5]):
                    print(f"   Job {i+1}: {job.get('company')} - {job.get('title')} (Score: {job.get('match_score', 0)})")
                    print(f"      Skills: {job.get('required_skills', [])}")
                
                return JSONResponse(content={
                    "success": True,
                    "message": "No matching internship opportunities were found for your skills. Consider updating your resume with more relevant technical skills.",
                    "jobs": matched_jobs[:5],  # Return jobs with scores for debugging
                    "skills_found": resume_skills,
                    "debug_info": {
                        "total_jobs_scraped": len(jobs),
                        "jobs_processed": len(matched_jobs),

                        "skills_extracted": len(resume_skills),
                        "all_job_scores": [{"company": job.get('company'), "title": job.get('title'), "score": job.get('match_score', 0)} for job in matched_jobs[:5]]
                    }
                })
            
            # Use jobs with matches for the success response
            matched_jobs = jobs_with_matches
            print(f"✅ Final matched jobs: {len(matched_jobs)}")
        except Exception as e:
            print(f"❌ Error matching jobs: {e}")
            raise HTTPException(status_code=500, detail=f"Error matching your resume to jobs: {str(e)}")

        # Clean up S3 file after processing
        if s3_key:
            try:
                delete_resume_from_s3(s3_key)
                print(f"🗑️ Cleaned up S3 file: {s3_key}")
            except Exception as cleanup_error:
                print(f"⚠️ Failed to clean up S3 file {s3_key}: {cleanup_error}")

        # Return JSON response for React frontend
        return JSONResponse(content={
            "success": True,
            "message": f"Found {len(matched_jobs)} matching opportunities!",
            "jobs": matched_jobs,
            "skills_found": resume_skills
        })

    except HTTPException:
        # Clean up S3 file on error
        if 's3_key' in locals() and s3_key:
            try:
                delete_resume_from_s3(s3_key)
                print(f"🗑️ Cleaned up S3 file after error: {s3_key}")
            except Exception as cleanup_error:
                print(f"⚠️ Failed to clean up S3 file {s3_key}: {cleanup_error}")
        raise
    except Exception as e:
        # Clean up S3 file on unexpected error
        if 's3_key' in locals() and s3_key:
            try:
                delete_resume_from_s3(s3_key)
                print(f"🗑️ Cleaned up S3 file after error: {s3_key}")
            except Exception as cleanup_error:
                print(f"⚠️ Failed to clean up S3 file {s3_key}: {cleanup_error}")
        
        print(f"❌ Unexpected error in api_match_resume: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected error occurred: {str(e)}. Please try again or contact support if the problem persists."
        )


@app.get("/api/resume-cache/{resume_hash}")
async def check_resume_cache(resume_hash: str, user_id: str = Query(...)):
    cached = get_resume_cache(user_id, resume_hash)
    if cached:
        return JSONResponse({"hit": True, "results": cached["results"], "skills": cached["skills"]})
    return JSONResponse({"hit": False})


@app.post("/api/match-stream")
async def stream_match_resume(
    resume: UploadFile = File(...),
    think_deeper: str = Form("true"),
    user_id: str = Form(default=""),
    resume_hash: str = Form(default=""),
):
    """Streaming endpoint that provides real-time progress updates"""
    
    # IMPORTANT: Read all file data BEFORE the generator function
    # to avoid "i/o operation on closed file" errors
    try:
        # Validate file
        if not resume:
            async def error_response():
                yield {"data": json.dumps({'error': 'No file was uploaded'})}
            return EventSourceResponse(error_response())

        file_extension = resume.filename.split('.')[-1].lower() if resume.filename else ''
        allowed_extensions = ['pdf', 'png', 'jpg', 'jpeg']
        
        if file_extension not in allowed_extensions:
            async def error_response():
                yield {"data": json.dumps({'error': f'Invalid file type: {file_extension}'})}
            return EventSourceResponse(error_response())

        # Read file content ONCE, before the generator
        file_content = await resume.read()
        filename = resume.filename
        content_type = resume.content_type
        
        if not file_content:
            async def error_response():
                yield {"data": json.dumps({'error': 'Empty file uploaded'})}
            return EventSourceResponse(error_response())

        # Upload file to S3 ONCE, before the generator
        try:
            print(f"📤 Stream: Starting S3 upload for {filename}...")
            s3_key = upload_resume_to_s3(file_content, filename)
            print(f"✅ Stream: Resume uploaded to S3: {s3_key}")
            print(f"🚀 Stream: About to start SSE generator...")
        except Exception as e:
            print(f"❌ Stream: S3 upload failed: {e}")
            error_msg = str(e)
            async def error_response():
                yield {"data": json.dumps({'error': f'S3 upload failed: {error_msg}'})}
            return EventSourceResponse(error_response())
    except Exception as e:
        error_msg = str(e)
        async def error_response():
            yield {"data": json.dumps({'error': f'File upload error: {error_msg}'})}
        return EventSourceResponse(error_response())
    
    async def generate_progress():
        try:
            print("🔄 SSE Generator started - sending initial connection event...")
            
            # Send immediate "connected" event to establish the stream
            # This ensures the client knows the connection is active
            yield f"data: {json.dumps({'step': 0, 'message': 'Connection established, starting analysis...', 'progress': 5})}\n\n"
            await asyncio.sleep(0.01)  # Tiny delay to flush
            print("✅ Initial SSE connection event sent")
            
            # Convert think_deeper parameter to boolean
            use_llm = think_deeper.lower() == "true"

            # Track current step and progress for dynamic updates
            current_step = [0]  # Use list to allow modification in nested function
            progress_queue = asyncio.Queue()  # Async queue for real-time progress messages
            loop = asyncio.get_running_loop()  # Get RUNNING event loop for thread-safe operations (critical for async generators)
            print(f"🔄 Event loop obtained: {loop}")

            def progress_callback(message):
                """Thread-safe callback function to queue progress messages"""
                current_step[0] += 1
                # Calculate progress percentage based on step and mode
                if use_llm:
                    # Deep Thinking Mode: More granular steps (up to 10+ steps)
                    progress_map = {
                        "Extracting text from resume...": 20,
                        "Analyzing resume with AI...": 30,
                        "Pre-filtering top candidates for you...": 60,
                        "Running AI career analysis": 70,  # Batch messages start here
                        "Enhancing results with career insights...": 90,
                    }
                else:
                    # Quick Mode: Fewer steps (7 total)
                    progress_map = {
                        "Extracting text from resume...": 20,
                        "Analyzing resume with AI...": 30,
                        "Matching jobs with keyword analysis...": 70,
                    }

                # Find matching progress or default
                progress = 50  # Default
                for key, value in progress_map.items():
                    if key in message:
                        progress = value
                        # For batch messages, calculate incremental progress
                        if "batch" in message and "of" in message:
                            try:
                                # Extract "batch X of Y" and calculate progress
                                parts = message.split("batch")[-1].strip()
                                batch_info = parts.split("of")
                                current_batch = int(batch_info[0].strip().split()[0])
                                total_batches = int(batch_info[1].strip().split()[0])
                                # Progress from 70% to 85% across batches
                                batch_progress = 70 + int((current_batch / total_batches) * 15)
                                progress = batch_progress
                            except:
                                pass
                        break

                # Thread-safe queue put (works from worker threads)
                asyncio.run_coroutine_threadsafe(
                    progress_queue.put({'step': current_step[0], 'message': message, 'progress': progress}),
                    loop
                )

            print("🔄 Yielding first SSE message (10% - Uploading resume)...")
            yield f"data: {json.dumps({'step': 1, 'message': 'Uploading resume to secure storage...', 'progress': 10})}\n\n"
            await asyncio.sleep(0.05)  # Small delay to ensure SSE flushes to client
            print("✅ First SSE message yielded successfully")

            # Download file from S3 for processing
            try:
                downloaded_content, original_filename = download_resume_from_s3(s3_key)
            except Exception as e:
                yield f"data: {json.dumps({'error': f'S3 download failed: {str(e)}'})}\n\n"
                return

            # Step 2: Parse resume with progress callbacks (in background thread)
            current_step[0] = 1  # Reset step counter for parse phase

            try:
                # Run parse_resume in background thread to avoid blocking event loop
                parse_task = asyncio.create_task(
                    asyncio.to_thread(
                        parse_resume,
                        downloaded_content,
                        original_filename,
                        use_llm,
                        progress_callback
                    )
                )

                # Yield progress messages in real-time as they arrive
                while not parse_task.done():
                    try:
                        # Wait for progress message with short timeout
                        progress_msg = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                        yield f"data: {json.dumps(progress_msg)}\n\n"
                        await asyncio.sleep(0.02)  # Small delay to ensure SSE flushes to client
                    except asyncio.TimeoutError:
                        # No message yet, continue waiting for task
                        await asyncio.sleep(0)  # Yield control to event loop
                        continue

                # Get the result after task completes
                resume_skills, resume_text, resume_metadata = await parse_task

                # Drain any remaining messages in queue
                while not progress_queue.empty():
                    try:
                        progress_msg = progress_queue.get_nowait()
                        yield f"data: {json.dumps(progress_msg)}\n\n"
                        await asyncio.sleep(0.02)  # Small delay to ensure SSE flushes to client
                    except asyncio.QueueEmpty:
                        break

                if not resume_skills:
                    yield f"data: {json.dumps({'error': 'No skills detected in resume'})}\n\n"
                    return

                exp_level = resume_metadata.get('experience_level', 'unknown')
                current_step[0] += 1
                yield f"data: {json.dumps({'step': current_step[0], 'message': f'Found {len(resume_skills)} skills in your resume', 'skills': resume_skills, 'progress': 45})}\n\n"
                await asyncio.sleep(0.05)  # Small delay to ensure SSE flushes to client

            except Exception as e:
                yield f"data: {json.dumps({'error': f'Resume parsing failed: {str(e)}'})}\n\n"
                # Clean up S3 file on error
                try:
                    delete_resume_from_s3(s3_key)
                except:
                    pass
                return

            # Step 3: Get jobs from cache or scrape
            current_step[0] += 1
            yield f"data: {json.dumps({'step': current_step[0], 'message': 'Loading internship opportunities...', 'progress': 55})}\n\n"
            await asyncio.sleep(0.05)  # Small delay to ensure SSE flushes to client

            try:
                jobs = await get_jobs_with_cache()
                if not jobs:
                    yield f"data: {json.dumps({'error': 'No jobs found'})}\n\n"
                    # Clean up S3 file on error
                    try:
                        delete_resume_from_s3(s3_key)
                    except:
                        pass
                    return

            except Exception as e:
                yield f"data: {json.dumps({'error': f'Job loading failed: {str(e)}'})}\n\n"
                # Clean up S3 file on error
                try:
                    delete_resume_from_s3(s3_key)
                except:
                    pass
                return

            # Step 4: Match jobs with progress callbacks (in background thread)
            try:
                # Run match_resume_to_jobs in background thread to avoid blocking event loop
                match_task = asyncio.create_task(
                    asyncio.to_thread(
                        match_resume_to_jobs,
                        resume_skills,
                        jobs,
                        resume_text,
                        use_llm,
                        progress_callback
                    )
                )

                # Yield progress messages in real-time as they arrive
                while not match_task.done():
                    try:
                        # Wait for progress message with short timeout
                        progress_msg = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                        yield f"data: {json.dumps(progress_msg)}\n\n"
                        await asyncio.sleep(0.02)  # Small delay to ensure SSE flushes to client
                    except asyncio.TimeoutError:
                        # No message yet, continue waiting for task
                        await asyncio.sleep(0)  # Yield control to event loop
                        continue

                # Get the result after task completes
                matched_jobs = await match_task

                # Drain any remaining messages in queue
                while not progress_queue.empty():
                    try:
                        progress_msg = progress_queue.get_nowait()
                        yield f"data: {json.dumps(progress_msg)}\n\n"
                        await asyncio.sleep(0.02)  # Small delay to ensure SSE flushes to client
                    except asyncio.QueueEmpty:
                        break
                
                # Convert to the format expected by frontend
                formatted_jobs = []
                for job in matched_jobs:
                    # Handle timestamp conversion - could be datetime or string
                    first_seen = job.get('first_seen')
                    last_seen = job.get('last_seen')

                    # Convert to ISO string if datetime object
                    if first_seen and hasattr(first_seen, 'isoformat'):
                        first_seen = first_seen.isoformat()
                    elif first_seen and not isinstance(first_seen, str):
                        first_seen = str(first_seen)

                    if last_seen and hasattr(last_seen, 'isoformat'):
                        last_seen = last_seen.isoformat()
                    elif last_seen and not isinstance(last_seen, str):
                        last_seen = str(last_seen)

                    job_result = {
                        'company': job.get('company', 'Unknown'),
                        'title': job.get('title', 'Unknown'),
                        'location': job.get('location', 'Unknown'),
                        'apply_link': job.get('apply_link', '#'),
                        'match_score': job.get('match_score', 0),
                        'match_description': job.get('match_description', ''),
                        'ai_reasoning': job.get('ai_reasoning'),  # Include AI reasoning data
                        'required_skills': job.get('required_skills', []),
                        'first_seen': first_seen,
                        'last_seen': last_seen
                    }
                    formatted_jobs.append(job_result)
                
                jobs_with_matches = [job for job in formatted_jobs if job['match_score'] > 0]

                # For think deeper mode: return all results since LLM processed all jobs
                # For quick mode: return up to 50 results (fast keyword matching can handle more)
                if use_llm:
                    final_results = formatted_jobs  # Return all LLM-analyzed jobs
                else:
                    final_results = formatted_jobs[:50] if len(formatted_jobs) >= 50 else formatted_jobs
                
                # Debug logging
                print(f"🔍 Streaming final results: {len(final_results)} jobs")
                for i, job in enumerate(final_results):
                    print(f"   Job {i+1}: {job['company']} - {job['title']} (Score: {job['match_score']})")
                
                # Update completion message based on mode and results
                if use_llm:
                    completion_message = f'Think Deeper analysis complete! Found {len(jobs_with_matches)} matches out of {len(final_results)} jobs analyzed.'
                else:
                    completion_message = f'Quick matching complete! Found {len(jobs_with_matches)} matching jobs.'

                # Clean up S3 file after successful processing
                try:
                    delete_resume_from_s3(s3_key)
                    print(f"🗑️ Stream: Cleaned up S3 file: {s3_key}")
                except Exception as cleanup_error:
                    print(f"⚠️ Stream: Failed to clean up S3 file {s3_key}: {cleanup_error}")

                # Save to resume cache if user is authenticated
                if user_id and resume_hash:
                    try:
                        set_resume_cache(user_id, resume_hash, final_results, resume_skills)
                        print(f"💾 Saved results to resume cache for user {user_id}")
                    except Exception as cache_err:
                        print(f"⚠️ Failed to save resume cache: {cache_err}")

                current_step[0] += 1
                yield f"data: {json.dumps({'step': current_step[0], 'message': completion_message, 'final_results': final_results, 'matches_found': len(jobs_with_matches), 'total_results': len(final_results), 'progress': 100, 'complete': True})}\n\n"
                await asyncio.sleep(0.05)  # Small delay to ensure final SSE flushes to client

            except Exception as e:
                print(f"❌ Error in intelligent matching: {e}")
                # The match_resume_to_jobs function already has automatic keyword fallback
                # So if we reach here, it means even the fallback failed
                yield f"data: {json.dumps({'error': f'Job matching failed: {str(e)}'})}\n\n"
                
                # Format results
                formatted_jobs = []
                for job in matched_jobs:
                    # Handle timestamp conversion - could be datetime or string
                    first_seen = job.get('first_seen')
                    last_seen = job.get('last_seen')

                    # Convert to ISO string if datetime object
                    if first_seen and hasattr(first_seen, 'isoformat'):
                        first_seen = first_seen.isoformat()
                    elif first_seen and not isinstance(first_seen, str):
                        first_seen = str(first_seen)

                    if last_seen and hasattr(last_seen, 'isoformat'):
                        last_seen = last_seen.isoformat()
                    elif last_seen and not isinstance(last_seen, str):
                        last_seen = str(last_seen)

                    job_result = {
                        'company': job.get('company', 'Unknown'),
                        'title': job.get('title', 'Unknown'),
                        'location': job.get('location', 'Unknown'),
                        'apply_link': job.get('apply_link', '#'),
                        'match_score': job.get('match_score', 0),
                        'match_description': job.get('match_description', ''),
                        'ai_reasoning': job.get('ai_reasoning'),  # Include AI reasoning data
                        'required_skills': job.get('required_skills', []),
                        'first_seen': first_seen,
                        'last_seen': last_seen
                    }
                    formatted_jobs.append(job_result)
                
                jobs_with_matches = [job for job in formatted_jobs if job['match_score'] > 0]
                
                # Fallback uses legacy matching - keep 10 result limit for speed
                final_results = formatted_jobs[:10] if len(formatted_jobs) >= 10 else formatted_jobs
                
                # Clean up S3 file after fallback processing
                try:
                    delete_resume_from_s3(s3_key)
                    print(f"🗑️ Stream: Cleaned up S3 file after fallback: {s3_key}")
                except Exception as cleanup_error:
                    print(f"⚠️ Stream: Failed to clean up S3 file {s3_key}: {cleanup_error}")

                yield f"data: {json.dumps({'step': 10, 'message': 'Matching complete!', 'final_results': final_results, 'matches_found': len(jobs_with_matches), 'total_results': len(final_results), 'progress': 100, 'complete': True})}\n\n"

        except Exception as e:
            # Clean up S3 file on unexpected error
            try:
                delete_resume_from_s3(s3_key)
                print(f"🗑️ Stream: Cleaned up S3 file after error: {s3_key}")
            except Exception as cleanup_error:
                print(f"⚠️ Stream: Failed to clean up S3 file {s3_key}: {cleanup_error}")
            
            yield f"data: {json.dumps({'error': f'Unexpected error: {str(e)}'})}\n\n"

    async def sse_generator():
        """Wrapper generator that converts string yields to proper SSE format for EventSourceResponse"""
        async for event in generate_progress():
            # EventSourceResponse expects dicts with 'data' key, not raw strings
            # Extract the JSON from "data: {...}\n\n" format
            if event.startswith("data: "):
                json_str = event[6:].strip()  # Remove "data: " prefix and trailing newlines
                if json_str:
                    yield {"data": json_str}
    
    return EventSourceResponse(
        sse_generator(),
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Pragma": "no-cache",
            "Expires": "0",
        },
        ping=5,  # Send ping every 5 seconds to keep connection alive
    )


@app.get("/api/cache-status")
async def cache_status():
    """Get comprehensive hybrid cache status and information"""
    cache_info = job_cache.get_cache_info()
    
    return JSONResponse({
        "hybrid_cache": cache_info,
        "redis_available": job_cache.is_redis_available(),
        "database_available": job_cache.is_database_available(),
        "cache_system": "hybrid_redis_database",
        "redis_ttl_hours": job_cache.CACHE_TTL / 3600,
        "features": {
            "incremental_scraping": True,
            "job_deduplication": True,
            "persistent_storage": True,
            "automatic_cleanup": True
        }
    })


@app.get("/api/test-matching")
async def test_matching():
    """Debug endpoint to test matching system with sample data"""
    try:
        # Sample test data
        resume_skills = ["Python", "JavaScript", "React"]
        resume_text = "Computer Science student with web development experience"
        
        sample_jobs = [
            {
                "title": "Software Engineer Intern",
                "company": "TestCorp",
                "description": "Python and JavaScript development",
                "location": "San Francisco, CA",
                "apply_link": "https://example.com/apply",
                "required_skills": []
            }
        ]
        
        # Test matching
        matched_jobs = match_resume_to_jobs(resume_skills, sample_jobs, resume_text)
        
        # Format for frontend
        formatted_jobs = []
        for job in matched_jobs:
            job_result = {
                'company': job.get('company', 'Unknown'),
                'title': job.get('title', 'Unknown'),
                'location': job.get('location', 'Unknown'),
                'apply_link': job.get('apply_link', '#'),
                'match_score': job.get('match_score', 0),
                'match_description': job.get('match_description', ''),
                'required_skills': job.get('required_skills', [])
            }
            formatted_jobs.append(job_result)
        
        return JSONResponse({
            "success": True,
            "message": f"Test completed - found {len(formatted_jobs)} matches",
            "jobs": formatted_jobs,
            "skills_found": resume_skills,
            "system_info": {
                "using_two_stage_matching": True,
                "llm_enabled": bool(os.getenv("OPENAI_API_KEY")),
                "job_count": len(formatted_jobs)
            }
        })
        
    except Exception as e:
        print(f"❌ Test matching error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "system_info": {
                "llm_enabled": bool(os.getenv("OPENAI_API_KEY"))
            }
        })


@app.post("/api/refresh-cache")
async def refresh_cache(force_full: bool = False, max_days_old: int = 30):
    """
    Manually refresh the hybrid cache system (admin endpoint)

    Args:
        force_full: If True, performs full scrape. If False, uses smart detection
        max_days_old: Filter to only get jobs posted within N days (default: 30 days for last month)
    """
    try:
        scrape_type = "full" if force_full else "smart"
        date_filter_msg = f" (last {max_days_old} days)" if max_days_old else ""
        print(f"🔄 Manual cache refresh requested ({scrape_type} scrape{date_filter_msg})...")
        
        # Clear Redis cache (keep database for deduplication)
        clear_result = job_cache.clear_cache()
        
        # Perform scraping based on force_full parameter
        if force_full:
            from job_scrapers.dispatcher import scrape_jobs_full
            jobs = await scrape_jobs_full(max_days_old=max_days_old)
        else:
            # Smart scraping (auto-detects incremental vs full)
            jobs = await scrape_jobs(max_days_old=max_days_old)
        
        if not jobs:
            # If no new jobs in incremental mode, that's okay
            if not force_full:
                cache_info = job_cache.get_cache_info()
                db_jobs = cache_info.get('database', {}).get('active_jobs', 0)
                return JSONResponse({
                    "success": True,
                    "message": f"No new jobs found{date_filter_msg}. {db_jobs} jobs already in database",
                    "new_jobs": 0,
                    "total_jobs": db_jobs,
                    "scrape_type": scrape_type,
                    "max_days_old": max_days_old
                })
            else:
                raise HTTPException(status_code=500, detail=f"No jobs scraped in full refresh{date_filter_msg}")
        
        # Store in hybrid cache system
        cache_result = job_cache.set_cached_jobs(jobs, cache_type='manual_refresh')
        
        return JSONResponse({
            "success": True,
            "message": f"Cache refreshed successfully{date_filter_msg}",
            "new_jobs": cache_result.get('new_jobs', 0),
            "total_jobs": cache_result.get('total_jobs', len(jobs)),
            "database_success": cache_result.get('database_success', False),
            "redis_success": cache_result.get('redis_success', False),
            "scrape_type": scrape_type,
            "max_days_old": max_days_old,
            "redis_ttl_hours": job_cache.CACHE_TTL / 3600
        })
    except Exception as e:
        print(f"❌ Error refreshing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Cache refresh failed: {str(e)}")


@app.post("/api/refresh-cache-incremental")
async def refresh_cache_incremental(max_days_old: int = 30):
    """
    Force incremental cache refresh (only new jobs)

    Args:
        max_days_old: Filter to only get jobs posted within N days (default: 30 days for last month)
    """
    try:
        date_filter_msg = f" (last {max_days_old} days)" if max_days_old else ""
        print(f"🔄 Incremental cache refresh requested{date_filter_msg}...")
        
        from job_scrapers.dispatcher import scrape_jobs_incremental
        jobs = await scrape_jobs_incremental(max_days_old=max_days_old)
        
        cache_result = job_cache.set_cached_jobs(jobs, cache_type='incremental_manual')
        
        return JSONResponse({
            "success": True,
            "message": f"Incremental refresh completed{date_filter_msg}",
            "new_jobs": cache_result.get('new_jobs', 0),
            "total_processed": len(jobs),
            "database_success": cache_result.get('database_success', False),
            "redis_success": cache_result.get('redis_success', False),
            "max_days_old": max_days_old
        })
    except Exception as e:
        print(f"❌ Error in incremental refresh: {e}")
        raise HTTPException(status_code=500, detail=f"Incremental refresh failed: {str(e)}")


@app.get("/api/database-stats")
async def database_stats():
    """Get detailed database statistics"""
    try:
        from job_database import get_database_stats
        stats = get_database_stats()

        return JSONResponse({
            "success": True,
            "database_stats": stats,
            "available": job_cache.is_database_available()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get database stats: {str(e)}")


@app.get("/api/refresh-health")
async def refresh_health():
    """Check the health of the cache refresh system"""
    try:
        from job_database import get_db, CacheMetadata, Job
        from datetime import datetime, timedelta
        import json

        db = get_db()
        try:
            # Get most recent cache operation
            latest_op = db.query(CacheMetadata).order_by(CacheMetadata.last_updated.desc()).first()

            # Get stats
            active_count = db.query(Job).filter(Job.is_active == True).count()
            now = datetime.utcnow()

            health_status = {
                "status": "healthy",
                "warnings": [],
                "info": {}
            }

            if latest_op:
                time_since_update = now - latest_op.last_updated
                hours_since = time_since_update.total_seconds() / 3600

                health_status["info"]["last_refresh"] = {
                    "time": latest_op.last_updated.isoformat(),
                    "hours_ago": round(hours_since, 1),
                    "type": latest_op.cache_type,
                    "status": latest_op.status,
                    "new_jobs": latest_op.new_jobs_added,
                    "total_jobs": latest_op.job_count
                }

                # Check if refresh is overdue (>26 hours = daily refresh likely failed)
                if hours_since > 26:
                    health_status["status"] = "unhealthy"
                    health_status["warnings"].append(f"No refresh in {round(hours_since, 1)}h - daily refresh may not be running")
                elif hours_since > 24:
                    health_status["status"] = "warning"
                    health_status["warnings"].append(f"Refresh slightly overdue ({round(hours_since, 1)}h)")
            else:
                health_status["status"] = "unknown"
                health_status["warnings"].append("No cache operations recorded in database")

            # Check active job count
            health_status["info"]["active_jobs"] = active_count

            if active_count == 0:
                health_status["status"] = "critical"
                health_status["warnings"].append("No active jobs in database")
            elif active_count < 50:
                if health_status["status"] == "healthy":
                    health_status["status"] = "warning"
                health_status["warnings"].append(f"Low active job count: {active_count}")

            # Check job age distribution
            active_jobs = db.query(Job).filter(Job.is_active == True).all()

            if active_jobs:
                old_jobs = 0
                recent_jobs = 0

                for job in active_jobs:
                    try:
                        metadata = json.loads(job.job_metadata) if job.job_metadata else {}
                        days_since = metadata.get('days_since_posted')

                        if days_since is not None:
                            if days_since > 21:  # More than 3 weeks
                                old_jobs += 1
                            elif days_since <= 7:  # Last week
                                recent_jobs += 1
                    except:
                        pass

                health_status["info"]["job_age_distribution"] = {
                    "recent_jobs_0_7d": recent_jobs,
                    "old_jobs_21plus_d": old_jobs,
                    "recent_percentage": round(recent_jobs / len(active_jobs) * 100, 1) if active_jobs else 0
                }

                if recent_jobs < len(active_jobs) * 0.15:  # Less than 15% recent
                    if health_status["status"] == "healthy":
                        health_status["status"] = "warning"
                    health_status["warnings"].append("Less than 15% of jobs are from last 7 days - may need refresh")

            return JSONResponse({
                "success": True,
                "health": health_status,
                "recommendation": (
                    "Run manual refresh with: curl -X POST /api/refresh-cache?max_days_old=30"
                    if health_status["status"] in ["unhealthy", "warning"]
                    else "System is healthy"
                )
            })

        finally:
            db.close()

    except Exception as e:
        print(f"❌ Error checking refresh health: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "health": {
                "status": "error",
                "warnings": [f"Health check failed: {str(e)}"]
            }
        }, status_code=500)



def _sanitize_filename(value: str) -> str:
    """Replace non-alphanumeric characters with underscores for safe filenames."""
    return re.sub(r"[^\w\-]", "_", value)


@app.post("/api/tailor-resume")
async def tailor_resume_endpoint(
    request: Request,
    resume: UploadFile = File(...),
    job_title: str = Form(...),
    company: str = Form(...),
    job_description: str = Form(default=""),
    user_id: str = Form(default="anonymous"),
):
    # Extract client IP for additional context
    client_ip = request.client.host if request.client else "unknown"
    
    print(f"\n[{datetime.utcnow().isoformat()}] 👔 TAILOR RESUME REQUEST START")
    print(f"👤 User ID: {user_id} | 🌐 IP: {client_ip}")
    print(f"🎯 Target Job: '{job_title}' at '{company}'")
    print(f"📄 Original Resume: {resume.filename}")
    print(f"📝 Description provided: {'Yes' if job_description.strip() else 'No'} ({len(job_description)} chars)")

    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        print(f"❌ Tailor error (User: {user_id}): Unsupported file format - {resume.filename}")
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported")

    file_content = await resume.read()
    if not file_content:
        print(f"❌ Tailor error (User: {user_id}): Uploaded file is empty")
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    import time
    start_time = time.time()

    try:
        pdf_bytes = _tailor_resume(file_content, job_title, company, job_description)
    except ValueError as e:
        print(f"❌ Tailor error (User: {user_id}): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        print(f"❌ Tailor error (User: {user_id}): pdflatex not found")
        raise HTTPException(status_code=500, detail="LaTeX compiler unavailable — pdflatex not found")
    except subprocess.TimeoutExpired:
        print(f"❌ Tailor error (User: {user_id}): pdflatex timed out")
        raise HTTPException(status_code=500, detail="LaTeX compilation timed out")
    except RuntimeError as e:
        print(f"❌ Tailor error (User: {user_id}): Runtime error - {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"❌ Tailor error (User: {user_id}): Unexpected error - {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Resume tailoring failed: {e}")

    execution_time = round(time.time() - start_time, 2)
    safe_company = _sanitize_filename(company)
    safe_title = _sanitize_filename(job_title)
    filename = f"resume_tailored_{safe_company}_{safe_title}.pdf"
    
    print(f"✅ Tailoring Complete for User: {user_id}")
    print(f"⏱️ Generation time: {execution_time} seconds | Result size: {len(pdf_bytes)} bytes")
    print(f"[{datetime.utcnow().isoformat()}] 👔 TAILOR RESUME REQUEST END\n")

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[
            ".",
            "resume_parser",
            "resume_tailor",
            "matching",
            "job_scrapers",
            "email_sender",
        ],
        reload_excludes=["frontend", "venv", ".git", "__pycache__"],
    )
