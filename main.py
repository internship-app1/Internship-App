from resume_parser.parse_resume import parse_resume
from job_scrapers.dispatcher import scrape_all_company_sites
from matching.matcher import match_resume_to_jobs
from email_sender.generate_email import generate_email


def main():
    resume = parse_resume("data/Murali Resume.png")
    resume_skills = resume["skills"]
    resume_text = resume.get("text", "")
    print("✅ Parsed Resume Skills:", resume_skills)

    jobs = scrape_all_company_sites(keyword="software engineering intern")
    print(f"\n🔍 Found {len(jobs)} job(s). Matching with AI...")

    results = match_resume_to_jobs(resume_skills, jobs, resume_text=resume_text)

    print(f"\n✅ Matched {len(results)} jobs. Top results:\n")

    for job in results[:10]:
        print(f"- {job['title']} at {job['company']} ({job['location']})")
        print(f"  Match Score: {job['match_score']}%")
        print(f"  Reasoning: {job.get('ai_reasoning', {}).get('reasoning', 'N/A')}")
        print(f"  Link: {job['apply_link']}\n")
        print("-" * 40)

if __name__ == "__main__":
    main() 
    