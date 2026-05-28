# llm_processing_node.py

from matching.matcher import match_resume_to_jobs

def llm_processing_node(profile, jobs, resume_text="", use_llm=False):
    """
    Matches jobs to the user's profile using the efficient batch matcher.
    Returns a list of jobs with match scores and AI reasoning.
    Pass use_llm=True to enable deep LLM re-ranking (Think Deeper mode).
    """
    return match_resume_to_jobs(
        profile.get("skills", []),
        jobs,
        resume_text=resume_text,
        use_llm=use_llm,
    )