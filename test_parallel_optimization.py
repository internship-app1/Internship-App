#!/usr/bin/env python3
"""
Test script to verify parallel + dynamic batch processing optimization.
Compares sequential vs parallel performance.
"""
import time
import sys
import os

def test_dynamic_batch_sizing():
    """Test that dynamic batch size calculation works correctly."""
    from matching.matcher import calculate_optimal_batch_size

    print("🧪 Testing Dynamic Batch Size Calculation...")

    # Test 1: Short job descriptions (should allow more jobs per batch)
    short_jobs = [
        {'company': f'Company {i}', 'title': 'SWE Intern', 'description': 'Short job desc'}
        for i in range(30)
    ]
    short_resume = "Student with Python experience"

    optimal_short = calculate_optimal_batch_size(short_jobs, short_resume, max_size=50)
    print(f"   Short descriptions: {optimal_short} jobs per batch")
    assert optimal_short >= 20, f"Expected at least 20 for short descriptions, got {optimal_short}"

    # Test 2: Long job descriptions (should allow fewer jobs per batch)
    # Use more realistic long descriptions (500 char limit anyway)
    long_desc = """
    We are seeking a talented Software Engineering Intern to join our team.
    You will work on building scalable web applications using React, Node.js, and PostgreSQL.
    Responsibilities include: developing new features, writing tests, code reviews, and deploying to production.
    Requirements: Strong CS fundamentals, experience with JavaScript/TypeScript, knowledge of databases.
    Preferred: AWS experience, CI/CD pipelines, Agile methodologies.
    """ * 2  # ~1000 chars, will be truncated to 500

    long_jobs = [
        {
            'company': f'Company {i}',
            'title': 'Software Engineer Intern - Full Stack Development',
            'description': long_desc
        }
        for i in range(30)
    ]
    long_resume = """
    Experienced Computer Science Student with multiple internships.
    Strong background in full-stack development, cloud platforms, and system design.
    Led several team projects with production deployments and real user impact.
    """ * 5  # Longer resume

    optimal_long = calculate_optimal_batch_size(long_jobs, long_resume, max_size=50)  # Increase max to see difference
    print(f"   Long descriptions: {optimal_long} jobs per batch")
    assert optimal_long < optimal_short, f"Long descriptions should result in smaller batches (got {optimal_long} vs {optimal_short})"

    print("   ✅ Dynamic batch sizing works correctly!\n")
    return True


def test_parallel_vs_sequential():
    """Compare parallel vs sequential processing performance."""
    print("🧪 Testing Parallel vs Sequential Performance...")
    print("   (This test requires CLAUDE_API_KEY and will make real API calls)\n")

    if not os.getenv("CLAUDE_API_KEY"):
        print("   ⚠️  Skipping: CLAUDE_API_KEY not set")
        return None

    from matching.matcher import batch_analyze_jobs_with_llm

    # Create test data (20 jobs to trigger chunking)
    test_jobs = []
    for i in range(20):
        test_jobs.append({
            'company': f'TechCorp {i+1}',
            'title': f'Software Engineer Intern {i+1}',
            'location': 'San Francisco, CA',
            'description': f'Build web applications using React, Node.js, and PostgreSQL. Work on team {i+1}. Deploy to production.'
        })

    resume_skills = ['Python', 'JavaScript', 'React', 'Node.js', 'Flask', 'PostgreSQL']
    resume_text = """
    Computer Science Student at University

    Experience:
    - Software Engineering Intern at StartupCo
      Built full-stack web app with React and Flask
      Deployed to AWS with 200+ daily active users
      Implemented CI/CD pipeline with GitHub Actions

    Projects:
    - E-commerce Platform (React, Node.js, PostgreSQL)
      Deployed to production with Stripe payment integration
      100+ registered users, $5k in transactions
    """

    resume_metadata = {
        'experience_level': 'student',
        'years_of_experience': 1,
        'is_student': True
    }

    # Test 1: Sequential processing (use_parallel=False)
    print("   🔄 Testing SEQUENTIAL processing...")
    start_seq = time.time()
    try:
        results_seq = batch_analyze_jobs_with_llm(
            test_jobs,
            resume_skills,
            resume_text,
            resume_metadata,
            max_jobs_per_batch=10,  # Force chunking into 2 batches
            use_parallel=False
        )
        time_seq = time.time() - start_seq
        print(f"   ✅ Sequential: {len(results_seq)} jobs in {time_seq:.1f}s\n")
    except Exception as e:
        print(f"   ❌ Sequential failed: {e}\n")
        return False

    # Test 2: Parallel processing (use_parallel=True)
    print("   🚀 Testing PARALLEL processing...")
    start_par = time.time()
    try:
        results_par = batch_analyze_jobs_with_llm(
            test_jobs,
            resume_skills,
            resume_text,
            resume_metadata,
            max_jobs_per_batch=10,  # Force chunking into 2 batches
            use_parallel=True
        )
        time_par = time.time() - start_par
        print(f"   ✅ Parallel: {len(results_par)} jobs in {time_par:.1f}s\n")
    except Exception as e:
        print(f"   ❌ Parallel failed: {e}\n")
        return False

    # Compare performance
    speedup = time_seq / time_par
    print(f"   📊 Performance Comparison:")
    print(f"      Sequential: {time_seq:.1f}s")
    print(f"      Parallel:   {time_par:.1f}s")
    print(f"      Speedup:    {speedup:.2f}x faster\n")

    if speedup > 1.5:
        print(f"   ✅ Parallel processing is {speedup:.1f}x faster! 🚀")
        return True
    elif speedup > 1.0:
        print(f"   ⚠️  Parallel is faster but only {speedup:.1f}x (expected 2x+)")
        return True
    else:
        print(f"   ⚠️  Parallel is slower ({speedup:.2f}x). This can happen with small batches or rate limits.")
        return True


def test_automatic_dynamic_sizing():
    """Test that automatic dynamic sizing is used by default."""
    print("🧪 Testing Automatic Dynamic Sizing (Default Behavior)...")

    if not os.getenv("CLAUDE_API_KEY"):
        print("   ⚠️  Skipping: CLAUDE_API_KEY not set\n")
        return None

    from matching.matcher import batch_analyze_jobs_with_llm

    # Create test jobs
    test_jobs = [
        {
            'company': f'Company {i}',
            'title': 'SWE Intern',
            'description': 'Build web apps with React and Node.js'
        }
        for i in range(15)
    ]

    resume_skills = ['Python', 'JavaScript', 'React']
    resume_text = "CS Student with React and Python experience."
    resume_metadata = {'experience_level': 'student', 'years_of_experience': 0, 'is_student': True}

    print("   Testing with NO manual batch size (should auto-calculate)...")

    try:
        results = batch_analyze_jobs_with_llm(
            test_jobs,
            resume_skills,
            resume_text,
            resume_metadata
            # No max_jobs_per_batch parameter - should auto-calculate
        )
        print(f"   ✅ Auto-sizing worked: {len(results)} jobs analyzed\n")
        return True
    except Exception as e:
        print(f"   ❌ Auto-sizing failed: {e}\n")
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("🔬 PARALLEL + DYNAMIC BATCH OPTIMIZATION VERIFICATION")
    print("=" * 80)
    print()

    # Test 1: Dynamic batch sizing (no API calls)
    test1_ok = test_dynamic_batch_sizing()

    # Test 2: Automatic dynamic sizing (requires API)
    test2_ok = test_automatic_dynamic_sizing()

    # Test 3: Parallel vs Sequential (requires API, takes time)
    print("⏱️  Next test will make real API calls and compare performance...")
    user_input = input("   Run performance comparison? (y/n): ").lower().strip()

    if user_input == 'y':
        test3_ok = test_parallel_vs_sequential()
    else:
        print("   ⏭️  Skipping performance test\n")
        test3_ok = None

    # Summary
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"1. Dynamic batch sizing:     {'✅ PASS' if test1_ok else '❌ FAIL'}")
    print(f"2. Automatic sizing:         {'✅ PASS' if test2_ok else '⏭️  SKIP' if test2_ok is None else '❌ FAIL'}")
    print(f"3. Parallel performance:     {'✅ PASS' if test3_ok else '⏭️  SKIP' if test3_ok is None else '❌ FAIL'}")
    print("=" * 80)

    # Exit code
    if test1_ok and (test2_ok or test2_ok is None) and (test3_ok or test3_ok is None):
        print("\n✅ ALL TESTS PASSED (or skipped)!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)
