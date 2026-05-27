import { useNavigate } from 'react-router-dom';
import { Sparkles, ArrowRight } from 'lucide-react';

function Hero() {
  const navigate = useNavigate();

  return (
    <div className="relative overflow-hidden">
      <div className="container mx-auto px-6 py-20 lg:py-28">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left column: text */}
          <div className="flex flex-col gap-7">
            <div className="inline-flex items-center gap-2 border border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-950/50 px-4 py-1.5 text-sm font-medium text-violet-700 dark:text-violet-300 w-fit rounded-md">
              <span className="h-2 w-2 rounded-full bg-violet-500 animate-pulse" />
              AI-Powered Internship Matching
            </div>

            <h1
              className="text-4xl md:text-5xl font-extrabold tracking-tight leading-none"
              style={{ fontFamily: 'Sora, sans-serif' }}
            >
              <span className="text-neutral-950 dark:text-neutral-50 block">Find your</span>
              <span className="font-bold text-violet-500 block my-1">perfect</span>
              <span className="text-neutral-950 dark:text-neutral-50 block">internship</span>
            </h1>

            <p className="text-lg text-neutral-600 dark:text-neutral-400 max-w-lg leading-relaxed">
              Upload your resume. Get matched to internships that actually fit your skills.
            </p>

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => navigate('/find')}
                className="inline-flex items-center justify-center gap-2 rounded-lg px-6 py-3 bg-violet-600 hover:bg-violet-700 text-white font-semibold shadow-lg shadow-violet-500/30 hover:-translate-y-0.5 transition-all text-sm w-full sm:w-auto"
              >
                <Sparkles className="w-4 h-4" />
                Upload Resume
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={() =>
                  document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })
                }
                className="inline-flex items-center justify-center gap-2 rounded-md px-6 py-3 border border-neutral-200 dark:border-neutral-700 hover:border-violet-300 dark:hover:border-violet-700 text-neutral-700 dark:text-neutral-300 font-semibold transition-all text-sm w-full sm:w-auto"
              >
                See How It Works
              </button>
            </div>
          </div>

          {/* Right column: sample match card */}
          <div className="flex justify-center lg:justify-end">
            <div className="w-full max-w-sm">
              <div className="rounded-xl border border-violet-100 dark:border-violet-900 bg-white dark:bg-neutral-900 shadow-xl shadow-violet-500/10 p-6 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-neutral-900 dark:text-neutral-100 text-base">
                      Software Engineer Intern
                    </h3>
                    <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">
                      Ramp · New York, NY · Summer 2026
                    </p>
                  </div>
                  <span className="font-bold text-violet-500 font-mono text-2xl leading-none">92%</span>
                </div>

                <div className="flex flex-wrap gap-1.5">
                  {['Python', 'React', 'TypeScript', 'REST APIs'].map((skill) => (
                    <span
                      key={skill}
                      className="text-xs font-mono px-2 py-0.5 rounded bg-violet-50 dark:bg-violet-950/50 text-violet-700 dark:text-violet-300 border border-violet-100 dark:border-violet-900"
                    >
                      {skill}
                    </span>
                  ))}
                </div>

                <p className="text-xs text-neutral-500 dark:text-neutral-400 leading-relaxed">
                  Strong match — your React and Python experience aligns directly with Ramp's fintech stack. 4 of 5 required skills detected.
                </p>

                <div className="pt-2 border-t border-neutral-100 dark:border-neutral-800 flex items-center justify-between">
                  <span className="text-xs text-green-600 font-medium flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-green-500 inline-block" />
                    NEW · Posted 3 hours ago
                  </span>
                  <span className="text-xs font-medium text-violet-600">Apply Now →</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export { Hero };
