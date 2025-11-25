#!/usr/bin/env python3
"""
Quick test script to verify batch LLM analysis handles truncation properly.
"""
import sys
import json

def test_batch_chunking():
    """Test that batch analysis automatically chunks large job lists."""
    from matching.matcher import batch_analyze_jobs_with_llm

    # Simulate a large batch of jobs (30+ jobs should trigger chunking)
    mock_jobs = []
    for i in range(25):
        mock_jobs.append({
            'company': f'Company {i+1}',
            'title': f'Software Engineer Intern {i+1}',
            'location': 'Remote',
            'description': 'Build web applications using React and Node.js'
        })

    resume_skills = ['Python', 'JavaScript', 'React', 'Node.js', 'Flask', 'PostgreSQL']
    resume_text = """
    Software Engineering Student at University

    Projects:
    - Built full-stack web app with React and Flask
    - Deployed app to AWS with 100+ users
    - Implemented CI/CD pipeline with GitHub Actions
    """

    resume_metadata = {
        'experience_level': 'student',
        'years_of_experience': 0,
        'is_student': True
    }

    print("🧪 Testing batch analysis with 25 jobs...")
    print(f"   Expected: Automatic chunking into batches of 20 jobs")

    try:
        # This should automatically chunk into 2 batches (20 + 5)
        results = batch_analyze_jobs_with_llm(
            mock_jobs,
            resume_skills,
            resume_text,
            resume_metadata,
            max_jobs_per_batch=20
        )

        print(f"\n✅ SUCCESS: Got {len(results)} job scores back")
        print(f"   Expected 25, got {len(results)}")

        if len(results) == 25:
            print("   ✅ All jobs were analyzed successfully!")
            return True
        else:
            print(f"   ⚠️  Warning: Expected 25 results but got {len(results)}")
            return False

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_json_validation():
    """Test that malformed JSON is caught and handled."""
    from matching.matcher import extract_json_from_response
    import json

    print("\n🧪 Testing JSON extraction and validation...")

    # Test 1: Valid JSON with markdown
    test1 = '''```json
{
  "score": 85,
  "reasoning": "Good match"
}
```'''

    try:
        result1 = extract_json_from_response(test1)
        parsed1 = json.loads(result1)
        print("   ✅ Test 1 passed: Valid JSON with markdown extracted")
    except Exception as e:
        print(f"   ❌ Test 1 failed: {e}")
        return False

    # Test 2: Truncated JSON (unterminated string)
    test2 = '''```json
{
  "score": 85,
  "reasoning": "This string is cut off mid-sente
```'''

    try:
        result2 = extract_json_from_response(test2)
        parsed2 = json.loads(result2)
        print("   ❌ Test 2 failed: Should have caught truncated JSON")
        return False
    except json.JSONDecodeError:
        print("   ✅ Test 2 passed: Truncated JSON caught correctly")
    except Exception as e:
        print(f"   ⚠️  Test 2 unexpected error: {e}")

    return True

if __name__ == "__main__":
    print("=" * 80)
    print("🔬 BATCH LLM ANALYSIS FIX VERIFICATION")
    print("=" * 80)

    # Test 1: JSON validation
    json_ok = test_json_validation()

    # Test 2: Batch chunking (requires CLAUDE_API_KEY)
    import os
    if os.getenv("CLAUDE_API_KEY"):
        print("\n" + "=" * 80)
        batch_ok = test_batch_chunking()
        print("=" * 80)

        if json_ok and batch_ok:
            print("\n✅ ALL TESTS PASSED!")
            sys.exit(0)
        else:
            print("\n❌ SOME TESTS FAILED")
            sys.exit(1)
    else:
        print("\n⚠️  Skipping batch chunking test (CLAUDE_API_KEY not set)")
        if json_ok:
            print("\n✅ JSON VALIDATION TESTS PASSED!")
            sys.exit(0)
        else:
            print("\n❌ JSON VALIDATION TESTS FAILED")
            sys.exit(1)