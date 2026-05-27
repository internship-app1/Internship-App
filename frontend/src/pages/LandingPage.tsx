import React, { useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInView } from 'framer-motion';
import Header from '../components/Header';
import { Hero } from '../components/ui/animated-hero';
import { FadeUp } from '../components/ui/fade-up';
import { Upload, Brain, CheckCircle2 } from 'lucide-react';

/* ─── Stat counter ───────────────────────────────────────────────────────── */
interface StatCounterProps {
  target: string;
  label: string;
}

function StatCounter({ target, label }: StatCounterProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });
  const hasAnimated = useRef(false);

  React.useEffect(() => {
    if (!isInView || hasAnimated.current) return;
    hasAnimated.current = true;

    const numericMatch = target.match(/[\d,]+/);
    if (!numericMatch || !ref.current) return;

    const rawNum = parseInt(numericMatch[0].replace(/,/g, ''), 10);
    const prefix = target.slice(0, target.indexOf(numericMatch[0]));
    const suffix = target.slice(target.indexOf(numericMatch[0]) + numericMatch[0].length);

    const duration = 1400;
    const startTime = performance.now();

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(eased * rawNum);

      if (ref.current) {
        const formatted = rawNum >= 1000 ? current.toLocaleString() : current.toString();
        ref.current.textContent = `${prefix}${formatted}${suffix}`;
      }

      if (progress < 1) requestAnimationFrame(tick);
    };

    requestAnimationFrame(tick);
  }, [isInView, target]);

  return (
    <div className="text-center">
      <span ref={ref} className="text-3xl md:text-4xl font-bold text-violet-600 block">
        {target}
      </span>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">{label}</p>
    </div>
  );
}

/* ─── Main page ──────────────────────────────────────────────────────────── */
const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main>
        {/* ── Hero ─────────────────────────────────────────────────── */}
        <Hero />

        {/* ── How It Works ─────────────────────────────────────────── */}
        <section id="how-it-works" className="py-16 px-4 border-t border-neutral-200 dark:border-neutral-800">
          <div className="container max-w-4xl mx-auto">
            <FadeUp className="mb-10">
              <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
                How it works
              </h2>
            </FadeUp>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                {
                  Icon: Upload,
                  title: 'Upload your resume',
                  desc: 'Drop a PDF or image. We extract your skills, frameworks, and experience level.',
                },
                {
                  Icon: Brain,
                  title: 'AI ranks every live posting',
                  desc: 'Claude reads your profile and scores live internships against what's actually in your resume.',
                },
                {
                  Icon: CheckCircle2,
                  title: 'Review matches and apply',
                  desc: 'Each result includes a match score and a plain-English explanation of why it fits.',
                },
              ].map(({ Icon, title, desc }, i) => (
                <FadeUp key={title} delay={i * 0.08}>
                  <div className="flex gap-4 items-start">
                    <div className="h-9 w-9 rounded-lg bg-violet-50 dark:bg-violet-950/50 border border-violet-100 dark:border-violet-900 flex items-center justify-center flex-shrink-0">
                      <Icon className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-1">
                        {title}
                      </h3>
                      <p className="text-sm text-neutral-500 dark:text-neutral-400 leading-relaxed">
                        {desc}
                      </p>
                    </div>
                  </div>
                </FadeUp>
              ))}
            </div>
          </div>
        </section>

        {/* ── Closing CTA ──────────────────────────────────────────── */}
        <section className="py-20 px-4 border-t border-neutral-200 dark:border-neutral-800">
          <div className="container max-w-3xl mx-auto text-center">
            <FadeUp>
              <h2 className="text-2xl md:text-3xl font-bold text-neutral-950 dark:text-neutral-50 mb-3">
                Upload your resume. See your top 10 matches in 30 seconds.
              </h2>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-8 max-w-md mx-auto">
                Free, no signup to try. Open-source on GitHub. Built by a student, used by real students.
              </p>
              <button
                onClick={() => navigate('/find')}
                className="inline-flex items-center gap-2 bg-violet-600 hover:bg-violet-700 text-white px-6 py-3 rounded-lg text-sm font-semibold transition hover:-translate-y-0.5"
              >
                Upload resume →
              </button>
            </FadeUp>
          </div>
        </section>

        {/* ── Footer ───────────────────────────────────────────────── */}
        <footer className="border-t border-neutral-200 dark:border-neutral-800 py-8 px-4">
          <div className="container max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-neutral-500 dark:text-neutral-400">
            <span className="font-medium text-neutral-700 dark:text-neutral-200">
              internshipmatcher
            </span>
            <p className="text-neutral-400 text-center">© 2025 internshipmatcher. Free to use.</p>
            <div className="flex items-center gap-5">
              <button type="button" className="hover:text-neutral-800 dark:hover:text-neutral-200 transition-colors">
                Privacy
              </button>
              <button type="button" className="hover:text-neutral-800 dark:hover:text-neutral-200 transition-colors">
                Terms
              </button>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
};

export default LandingPage;
