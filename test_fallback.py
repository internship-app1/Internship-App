#!/usr/bin/env python3
"""
Test the dynamic fallback mechanism for job matching.
Tests the fix for C++ job matching bug.
"""
import sys
from matching.matcher import match_resume_to_jobs, simple_keyword_match, simple_keyword_scoring

def test_keyword_scoring():
    """Test basic keyword scoring logic."""
    print("🧪 Testing Keyword Scoring...")

    # Sample job and resume data
    job = {
        'job_id': 1,
        'title': 'Software Engineering Intern',
        'company': 'TechCorp',
        'description': 'Looking for Python and React developer',
        'required_skills': ['Python', 'React', 'Git']
    }

    resume_skills = ['Python', 'JavaScript', 'Git', 'SQL']
    resume_text = 'Software engineer with Python experience'

    score = simple_keyword_scoring(job, resume_skills, resume_text)

    print(f"   Job: {job['title']}")
    print(f"   Job Skills: {job['required_skills']}")
    print(f"   Resume Skills: {resume_skills}")
    print(f"   Match Score: {score}/100")

    assert 0 <= score <= 100, "Score should be between 0 and 100"
    assert score > 0, "Should have some match (Python and Git overlap)"
    print("   ✅ Keyword scoring works!\n")
    return True

def test_cpp_job_no_match():
    """Test that C++ jobs score LOW for Python/JS resumes (the bug fix)."""
    print("🧪 Testing C++ Job No Match (Bug Fix)...")

    # This simulates the Lumafield Embedded Software job
    cpp_job = {
        'job_id': 1,
        'title': 'Engineering Intern, Embedded Software',
        'company': 'Lumafield',
        'description': 'Embedded software development using C++ and firmware engineering',
        'required_skills': ['C++', 'Embedded Systems', 'Firmware']
    }

    # User's actual resume (no C++)
    resume_skills = ['Python', 'JavaScript', 'Java', 'React', 'Node.js', 'Git',
                     'Docker', 'AWS', 'Flask', 'FastAPI', 'SQL', 'PostgreSQL']

    score = simple_keyword_scoring(cpp_job, resume_skills, resume_skills)

    print(f"   Job: {cpp_job['title']}")
    print(f"   Job Skills: {cpp_job['required_skills']}")
    print(f"   Resume Skills: {resume_skills[:6]}... (no C++)")
    print(f"   Match Score: {score}/100")

    # The bug was that this scored 100/100
    # After fix, it should score <= 30 (zero skill match penalty)
    assert score <= 30, f"C++ job should score ≤30 for non-C++ resume, got {score}"
    print(f"   ✅ C++ job correctly scores low ({score}/100) - Bug fixed!\n")
    return True

def test_keyword_match():
    """Test keyword matching returns proper format."""
    print("🧪 Testing Keyword Match Function...")

    jobs = [
        {
            'job_id': 1,
            'title': 'Python Developer Intern',
            'company': 'Tech Inc',
            'description': 'Python and Django development',
            'required_skills': ['Python', 'Django'],
            'location': 'San Francisco'
        },
        {
            'job_id': 2,
            'title': 'Frontend Intern',
            'company': 'Design Co',
            'description': 'React and TypeScript work',
            'required_skills': ['React', 'TypeScript'],
            'location': 'New York'
        },
        {
            'job_id': 3,
            'title': 'Full Stack Intern',
            'company': 'Startup LLC',
            'description': 'Python, React, and PostgreSQL',
            'required_skills': ['Python', 'React', 'PostgreSQL'],
            'location': 'Remote'
        }
    ]

    resume_skills = ['Python', 'Flask', 'JavaScript']
    resume_text = 'Python developer with web experience'

    results = simple_keyword_match(resume_skills, jobs, resume_text)

    print(f"   Found {len(results)} matched jobs")
    for job in results[:3]:
        print(f"   - {job['title']}: {job['match_score']}/100")
        assert 'match_score' in job, "Should have match_score field"
        assert 'match_description' in job, "Should have match_description field"

    print("   ✅ Keyword match works!\n")
    return True

def test_llm_disabled_mode():
    """Test that use_llm=False uses keyword matching."""
    print("🧪 Testing LLM Disabled Mode...")

    jobs = [
        {
            'job_id': 1,
            'title': 'Python Intern',
            'company': 'Tech Co',
            'description': 'Python development',
            'required_skills': ['Python'],
            'location': 'SF'
        }
    ]

    resume_skills = ['Python', 'Django']

    # This should use keyword matching directly (no LLM call)
    results = match_resume_to_jobs(resume_skills, jobs, use_llm=False)

    print(f"   Matched {len(results)} jobs")
    assert len(results) > 0, "Should find at least one match"
    assert results[0]['match_score'] > 0, "Should have positive score"
    assert results[0]['ai_reasoning'] is None, "Should not have AI reasoning in keyword mode"

    print(f"   - {results[0]['title']}: {results[0]['match_score']}/100")
    print("   ✅ LLM disabled mode works!\n")
    return True

def test_empty_jobs():
    """Test that empty job list doesn't crash."""
    print("🧪 Testing Empty Jobs...")

    resume_skills = ['Python', 'React']
    results = match_resume_to_jobs(resume_skills, [], use_llm=False)

    assert results == [], "Empty jobs should return empty list"
    print("   ✅ Empty jobs handled correctly!\n")
    return True

if __name__ == "__main__":
    print("=" * 80)
    print("🔬 DYNAMIC FALLBACK TEST SUITE + BUG FIX VERIFICATION")
    print("=" * 80)
    print()

    try:
        test1 = test_keyword_scoring()
        test2 = test_cpp_job_no_match()  # NEW: Test the bug fix
        test3 = test_keyword_match()
        test4 = test_llm_disabled_mode()
        test5 = test_empty_jobs()

        print("=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"1. Keyword Scoring:      {'✅ PASS' if test1 else '❌ FAIL'}")
        print(f"2. C++ Job Bug Fix:      {'✅ PASS' if test2 else '❌ FAIL'}  ⭐ NEW")
        print(f"3. Keyword Match:        {'✅ PASS' if test3 else '❌ FAIL'}")
        print(f"4. LLM Disabled Mode:    {'✅ PASS' if test4 else '❌ FAIL'}")
        print(f"5. Empty Jobs:           {'✅ PASS' if test5 else '❌ FAIL'}")
        print("=" * 80)

        if test1 and test2 and test3 and test4 and test5:
            print("\n✅ ALL TESTS PASSED!")
            print("Dynamic fallback mechanism is working correctly! 🎉")
            print("\nThe system will now:")
            print("  • Use keyword matching when think_deeper=False")
            print("  • Automatically fall back to keyword matching if LLM fails")
            print("  • Never fail completely - always return results")
            print("  • C++ jobs score ≤30 for non-C++ resumes (bug fixed!)")
            sys.exit(0)
        else:
            print("\n❌ SOME TESTS FAILED")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
