import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

function Hero() {
  const navigate = useNavigate();
  const [titleNumber, setTitleNumber] = useState(0);
  const titles = useMemo(
    () => ['dream', 'perfect', 'next', 'ideal', 'future'],
    []
  );

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setTitleNumber((prev) => (prev === titles.length - 1 ? 0 : prev + 1));
    }, 2200);
    return () => clearTimeout(timeoutId);
  }, [titleNumber, titles]);

  return (
    <div className="hero-bg relative overflow-hidden">
      {/* Floating orbs */}
      <div
        className="pointer-events-none absolute top-[-80px] left-[-80px] h-[420px] w-[420px] rounded-full opacity-30"
        style={{
          background: 'radial-gradient(circle, hsl(263 70% 68% / 0.35) 0%, transparent 70%)',
          animation: 'float-orb 12s ease-in-out infinite',
        }}
      />
      <div
        className="pointer-events-none absolute bottom-[-60px] right-[-40px] h-[320px] w-[320px] rounded-full opacity-20"
        style={{
          background: 'radial-gradient(circle, hsl(187 85% 53% / 0.4) 0%, transparent 70%)',
          animation: 'float-orb 16s ease-in-out infinite reverse',
        }}
      />

      <div className="container mx-auto px-6 py-20 lg:py-28">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left column: text */}
          <div className="flex flex-col gap-7">
            {/* Eyebrow pill */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            >
              <div className="inline-flex items-center gap-2 rounded-full border border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-950/50 px-4 py-1.5 text-sm font-medium text-violet-700 dark:text-violet-300">
                <span className="h-2 w-2 rounded-full bg-violet-500 animate-pulse" />
                AI-Powered Internship Matching
              </div>
            </motion.div>

            {/* Headline */}
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
            >
              <h1
                className="text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-tight leading-none"
                style={{ fontFamily: 'Sora, sans-serif' }}
              >
                <span className="text-neutral-950 dark:text-neutral-50 block">Find your</span>

                {/* Cycling word */}
                <span className="relative block h-[1.15em] overflow-hidden my-1">
                  {titles.map((title, index) => (
                    <motion.span
                      key={index}
                      className="gradient-text absolute inset-0 flex items-center"
                      initial={{ opacity: 0, y: 60, filter: 'blur(4px)' }}
                      animate={
                        titleNumber === index
                          ? { opacity: 1, y: 0, filter: 'blur(0px)' }
                          : {
                              opacity: 0,
                              y: titleNumber > index ? -60 : 60,
                              filter: 'blur(4px)',
                            }
                      }
                      transition={{
                        type: 'spring',
                        stiffness: 260,
                        damping: 20,
                      }}
                    >
                      {title}
                    </motion.span>
                  ))}
                </span>

                <span className="text-neutral-950 dark:text-neutral-50 block">internship</span>
              </h1>
            </motion.div>

            {/* Subtitle */}
            <motion.p
              className="text-lg md:text-xl text-neutral-600 dark:text-neutral-400 max-w-lg font-normal leading-relaxed"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.22, ease: [0.22, 1, 0.36, 1] }}
            >
              Upload your resume. Get matched to internships that actually fit
              your skills — in seconds.
            </motion.p>

            {/* CTA buttons */}
            <motion.div
              className="flex flex-row gap-3 flex-wrap"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.32, ease: [0.22, 1, 0.36, 1] }}
            >
              <button
                onClick={() => navigate('/find')}
                className="inline-flex items-center gap-2 rounded-full px-8 py-4 bg-violet-600 hover:bg-violet-700 text-white font-semibold shadow-lg shadow-violet-500/30 hover:-translate-y-0.5 transition-all text-sm"
              >
                <Sparkles className="w-4 h-4" />
                Get Started — Upload Resume
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={() =>
                  document
                    .getElementById('how-it-works')
                    ?.scrollIntoView({ behavior: 'smooth' })
                }
                className="inline-flex items-center gap-2 rounded-full px-8 py-4 border-2 border-neutral-200 dark:border-neutral-700 hover:border-violet-200 dark:hover:border-violet-700 hover:bg-violet-50/50 dark:hover:bg-violet-950/30 text-neutral-700 dark:text-neutral-300 font-semibold transition-all text-sm"
              >
                See How It Works
              </button>
            </motion.div>
          </div>

          {/* Right column: mock job card preview */}
          <motion.div
            className="flex justify-center lg:justify-end"
            initial={{ opacity: 0, x: 32 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.65, delay: 0.18, ease: [0.22, 1, 0.36, 1] }}
          >
            <motion.div
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
              className="w-full max-w-sm"
            >
              {/* Card preview */}
              <div className="rounded-2xl border border-violet-100 dark:border-violet-900 bg-white dark:bg-neutral-900 shadow-2xl shadow-violet-500/10 p-6 space-y-4">
                {/* Header row */}
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-neutral-900 dark:text-neutral-100 text-base" style={{ fontFamily: 'Sora, sans-serif' }}>
                      Software Engineer Intern
                    </h3>
                    <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">Stripe · San Francisco, CA</p>
                  </div>
                  <span className="gradient-text font-mono font-bold text-2xl leading-none">92%</span>
                </div>

                {/* Skill badges */}
                <div className="flex flex-wrap gap-1.5">
                  {['Python', 'React', 'SQL', 'REST APIs'].map((skill) => (
                    <span
                      key={skill}
                      className="text-xs font-mono px-2 py-0.5 rounded-full bg-violet-50 dark:bg-violet-950/50 text-violet-700 dark:text-violet-300 border border-violet-100 dark:border-violet-900"
                    >
                      {skill}
                    </span>
                  ))}
                </div>

                {/* Match summary */}
                <p className="text-xs text-neutral-500 dark:text-neutral-400 leading-relaxed">
                  Strong match — your Python and React experience directly aligns
                  with their stack. 4 of 5 required skills detected.
                </p>

                {/* Footer row */}
                <div className="pt-2 border-t border-neutral-100 dark:border-neutral-800 flex items-center justify-between">
                  <span className="text-xs text-green-600 font-medium flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-green-500 inline-block" />
                    NEW · Posted 2 hours ago
                  </span>
                  <button className="text-xs font-medium text-violet-600 hover:text-violet-800 transition-colors">
                    Apply Now →
                  </button>
                </div>
              </div>

              {/* Decorative second card behind */}
              <div className="mt-3 mx-4 h-4 rounded-b-2xl border border-violet-100 dark:border-violet-900 bg-white/60 dark:bg-neutral-900/60 shadow-lg shadow-violet-500/5" />
            </motion.div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

export { Hero };
