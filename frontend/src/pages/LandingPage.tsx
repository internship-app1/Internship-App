import React, { useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useInView } from 'framer-motion';
import Header from '../components/Header';
import { Hero } from '../components/ui/animated-hero';
import { FadeUp } from '../components/ui/fade-up';
import {
  Sparkles,
  Zap,
  Target,
  TrendingUp,
  Upload,
  Brain,
  CheckCircle2,
  Database,
  Shield,
  Gift,
  Star,
} from 'lucide-react';

/* ─── Animated counter ───────────────────────────────────────────────── */
interface StatCounterProps {
  target: string; // e.g. "10,000+", "95%", "< 30s"
  label: string;
}

function StatCounter({ target, label }: StatCounterProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });
  const hasAnimated = useRef(false);

  React.useEffect(() => {
    if (!isInView || hasAnimated.current) return;
    hasAnimated.current = true;

    // Extract numeric prefix so we can count it, keep suffix as-is
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
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(eased * rawNum);

      if (ref.current) {
        const formatted =
          rawNum >= 1000 ? current.toLocaleString() : current.toString();
        ref.current.textContent = `${prefix}${formatted}${suffix}`;
      }

      if (progress < 1) {
        requestAnimationFrame(tick);
      }
    };

    requestAnimationFrame(tick);
  }, [isInView, target]);

  return (
    <div className="text-center">
      <span
        ref={ref}
        className="text-3xl md:text-4xl font-bold text-violet-600 block"
        style={{ fontFamily: 'Sora, sans-serif' }}
      >
        {target}
      </span>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">{label}</p>
    </div>
  );
}

/* ─── Stagger variants ───────────────────────────────────────────────── */
const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.12 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 24, scale: 0.98 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] as any },
  },
};

/* ─── Main page ──────────────────────────────────────────────────────── */
const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main>
        {/* ── Section 1: Hero ─────────────────────────────────────── */}
        <Hero />

        {/* ── Section 2: Stats Bar ────────────────────────────────── */}
        <section className="border-y border-neutral-200 dark:border-neutral-800 bg-neutral-50/80 dark:bg-neutral-900/80 py-10 px-4">
          <FadeUp>
            <div className="container max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8">
              <StatCounter target="10,000+" label="Internships indexed" />
              <StatCounter target="95%" label="Match accuracy" />
              <StatCounter target="500+" label="Companies hiring" />
              {/* Non-numeric stat — render static */}
              <div className="text-center">
                <span
                  className="text-3xl md:text-4xl font-bold text-violet-600 block"
                  style={{ fontFamily: 'Sora, sans-serif' }}
                >
                  &lt; 30s
                </span>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Time to first match</p>
              </div>
            </div>
          </FadeUp>
        </section>

        {/* ── Section 3: Features Bento Grid ──────────────────────── */}
        <section id="features" className="py-24 px-4">
          <div className="container max-w-5xl mx-auto">
            <FadeUp className="text-center mb-14">
              <p className="text-xs font-semibold tracking-widest uppercase text-violet-500 mb-3">
                What we do
              </p>
              <h2
                className="text-4xl md:text-5xl font-bold text-neutral-950 dark:text-neutral-50"
                style={{ fontFamily: 'Sora, sans-serif' }}
              >
                Everything you need to{' '}
                <span
                  style={{
                    background: 'linear-gradient(135deg,#7C3AED,#22D3EE)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  land the role
                </span>
              </h2>
            </FadeUp>

            <motion.div
              className="grid grid-cols-6 gap-4"
              variants={containerVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-60px' }}
            >
              {/* Large card */}
              <motion.div
                variants={itemVariants}
                className="col-span-6 md:col-span-3 row-span-2 relative overflow-hidden rounded-3xl bg-gradient-to-br from-violet-600 to-violet-800 p-8 flex flex-col justify-end min-h-[280px] text-white"
              >
                {/* Decorative circles */}
                <div className="absolute -top-10 -right-10 h-48 w-48 rounded-full bg-white/10" />
                <div className="absolute top-16 -right-6 h-28 w-28 rounded-full bg-cyan-400/20" />

                <div className="relative z-10">
                  <div className="h-12 w-12 rounded-2xl bg-white/20 flex items-center justify-center mb-5">
                    <Zap className="h-6 w-6 text-white" />
                  </div>
                  <h3
                    className="text-2xl font-bold mb-2"
                    style={{ fontFamily: 'Sora, sans-serif' }}
                  >
                    Lightning Fast Matching
                  </h3>
                  <p className="text-white/70 text-sm leading-relaxed max-w-xs">
                    Our AI scans thousands of live internship listings and ranks them against
                    your actual skills — not keywords — in seconds.
                  </p>
                </div>
              </motion.div>

              {/* Card 2 */}
              <motion.div
                variants={itemVariants}
                className="col-span-6 md:col-span-3 rounded-3xl bg-gradient-to-br from-cyan-50 to-white dark:from-cyan-950/30 dark:to-neutral-900 border border-cyan-100 dark:border-cyan-900/50 p-6"
              >
                <div className="h-11 w-11 rounded-2xl bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center mb-4 shadow-lg shadow-cyan-400/25">
                  <Target className="h-5 w-5 text-white" />
                </div>
                <h3
                  className="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2"
                  style={{ fontFamily: 'Sora, sans-serif' }}
                >
                  Smart Skill Detection
                </h3>
                <p className="text-neutral-500 dark:text-neutral-400 text-sm leading-relaxed">
                  We read your resume the way a recruiter does — pulling out real skills,
                  frameworks, and experience levels, not just raw text.
                </p>
              </motion.div>

              {/* Card 3 */}
              <motion.div
                variants={itemVariants}
                className="col-span-6 md:col-span-3 rounded-3xl bg-gradient-to-br from-violet-50 to-white dark:from-violet-950/30 dark:to-neutral-900 border border-violet-100 dark:border-violet-900/50 p-6"
              >
                <div className="h-11 w-11 rounded-2xl bg-gradient-to-br from-violet-500 to-violet-700 flex items-center justify-center mb-4 shadow-lg shadow-violet-500/25">
                  <TrendingUp className="h-5 w-5 text-white" />
                </div>
                <h3
                  className="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2"
                  style={{ fontFamily: 'Sora, sans-serif' }}
                >
                  Compatibility Scoring
                </h3>
                <p className="text-neutral-500 dark:text-neutral-400 text-sm leading-relaxed">
                  Every result comes with a match score and an explanation — so you know exactly
                  why a role is a fit before you apply.
                </p>
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* ── Section 4: How It Works ──────────────────────────────── */}
        <section id="how-it-works" className="py-24 px-4 bg-neutral-50/60 dark:bg-neutral-900/40">
          <div className="container max-w-5xl mx-auto">
            <FadeUp className="text-center mb-16">
              <p className="text-xs font-semibold tracking-widest uppercase text-violet-500 mb-3">
                The Process
              </p>
              <h2
                className="text-4xl md:text-5xl font-bold text-neutral-950 dark:text-neutral-50"
                style={{ fontFamily: 'Sora, sans-serif' }}
              >
                Three steps to your{' '}
                <span
                  style={{
                    background: 'linear-gradient(135deg,#7C3AED,#22D3EE)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  perfect match
                </span>
              </h2>
            </FadeUp>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  num: '01',
                  Icon: Upload,
                  title: 'Upload Your Resume',
                  desc: 'Drop your PDF or image resume. Our system instantly extracts your skills, experience, and education.',
                },
                {
                  num: '02',
                  Icon: Brain,
                  title: 'AI Analysis & Matching',
                  desc: 'Our AI reads your profile and scores thousands of internships by how well they actually fit you.',
                },
                {
                  num: '03',
                  Icon: CheckCircle2,
                  title: 'Review & Apply',
                  desc: 'See ranked matches with an explanation for each score. Apply directly with one click.',
                },
              ].map(({ num, Icon, title, desc }, i) => (
                <FadeUp key={num} delay={i * 0.1}>
                  <div className="relative flex flex-col items-center text-center px-4">
                    {/* Watermark number */}
                    <span
                      className="absolute -top-4 left-1/2 -translate-x-1/2 text-[96px] font-black text-neutral-100 dark:text-neutral-800 leading-none select-none pointer-events-none z-0"
                      style={{ fontFamily: 'Sora, sans-serif' }}
                    >
                      {num}
                    </span>

                    {/* Icon */}
                    <div className="relative z-10 h-14 w-14 rounded-2xl bg-gradient-to-br from-violet-500 to-violet-700 flex items-center justify-center shadow-lg shadow-violet-500/30 mb-5">
                      <Icon className="h-6 w-6 text-white" />
                    </div>

                    <h3
                      className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2 relative z-10"
                      style={{ fontFamily: 'Sora, sans-serif' }}
                    >
                      {title}
                    </h3>
                    <p className="text-sm text-neutral-500 dark:text-neutral-400 leading-relaxed relative z-10">
                      {desc}
                    </p>
                  </div>
                </FadeUp>
              ))}
            </div>
          </div>
        </section>

        {/* ── Section 5: Testimonials ──────────────────────────────── */}
        <section className="py-24 px-4 bg-gradient-to-br from-neutral-950 via-neutral-900 to-violet-950">
          <div className="container max-w-5xl mx-auto">
            <FadeUp className="text-center mb-14">
              <h2
                className="text-4xl md:text-5xl font-bold text-white mb-4"
                style={{ fontFamily: 'Sora, sans-serif' }}
              >
                Students land their{' '}
                <span
                  style={{
                    background: 'linear-gradient(135deg,#a78bfa,#22D3EE)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  dream internships
                </span>
              </h2>
              <p className="text-neutral-400 text-lg">
                Real results from students just like you.
              </p>
            </FadeUp>

            <motion.div
              className="grid grid-cols-1 md:grid-cols-3 gap-6"
              variants={containerVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-60px' }}
            >
              {[
                {
                  quote:
                    'Got matched to my Stripe internship in under 2 minutes. The AI actually explained WHY I was a good fit — way better than just seeing a job title.',
                  initials: 'JL',
                  name: 'Jamie L.',
                  role: 'CS · UC Berkeley → Software Intern at Stripe',
                },
                {
                  quote:
                    'I uploaded my resume on a Tuesday, had 3 interviews by Friday. internshipmatcher AI found roles I never would have found myself.',
                  initials: 'PS',
                  name: 'Priya S.',
                  role: 'Data Science · Georgia Tech → Data Analyst at Airbnb',
                },
                {
                  quote:
                    'The skill gap analysis told me exactly what to learn before applying. Got the job after adding one project to my GitHub.',
                  initials: 'MC',
                  name: 'Marcus C.',
                  role: 'Computer Eng · UT Austin → Product Intern at Figma',
                },
              ].map(({ quote, initials, name, role }, i) => (
                <motion.div
                  key={i}
                  variants={itemVariants}
                  className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-6 space-y-4"
                >
                  {/* Stars */}
                  <div className="flex gap-0.5">
                    {Array.from({ length: 5 }).map((_, s) => (
                      <Star
                        key={s}
                        className="h-4 w-4 fill-yellow-400 text-yellow-400"
                      />
                    ))}
                  </div>

                  <p className="text-white/80 text-sm leading-relaxed italic">
                    "{quote}"
                  </p>

                  <div className="border-t border-white/10 pt-4 flex items-center gap-3">
                    <div className="h-9 w-9 rounded-full bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                      {initials}
                    </div>
                    <div>
                      <p className="text-white text-sm font-semibold">{name}</p>
                      <p className="text-white/50 text-xs">{role}</p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ── Section 6: Why Choose Us ─────────────────────────────── */}
        <section className="py-24 px-4">
          <div className="container max-w-5xl mx-auto">
            <FadeUp className="text-center mb-12">
              <p className="text-xs font-semibold tracking-widest uppercase text-violet-500 mb-3">
                Why internshipmatcher AI
              </p>
              <h2
                className="text-4xl md:text-5xl font-bold text-neutral-950 dark:text-neutral-50"
                style={{ fontFamily: 'Sora, sans-serif' }}
              >
                Built for students,
                <br />
                powered by AI
              </h2>
            </FadeUp>

            <motion.div
              className="grid grid-cols-1 md:grid-cols-2 gap-6"
              variants={containerVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-60px' }}
            >
              {[
                {
                  Icon: Database,
                  gradient: 'from-violet-500 to-violet-700',
                  shadow: 'shadow-violet-500/25',
                  title: '10,000+ Live Internships',
                  desc: 'Sourced from GitHub\'s internship list, LinkedIn, and direct company boards. Updated daily so you never miss a new posting.',
                },
                {
                  Icon: Zap,
                  gradient: 'from-cyan-400 to-cyan-600',
                  shadow: 'shadow-cyan-400/25',
                  title: 'Results in Under 30 Seconds',
                  desc: 'No waiting. Upload, match, apply — the whole process is instant. Resume cached so repeat visits are even faster.',
                },
                {
                  Icon: Shield,
                  gradient: 'from-emerald-400 to-emerald-600',
                  shadow: 'shadow-emerald-400/25',
                  title: 'Your Data, Your Control',
                  desc: 'Your resume is analyzed and never shared with third parties. We cache results to help you — not to sell your data.',
                },
                {
                  Icon: Gift,
                  gradient: 'from-amber-400 to-orange-500',
                  shadow: 'shadow-amber-400/25',
                  title: 'Completely Free',
                  desc: 'No paywalls, no subscriptions, no hidden fees. internshipmatcher AI is free to use, forever.',
                },
              ].map(({ Icon, gradient, shadow, title, desc }, i) => (
                <motion.div
                  key={i}
                  variants={itemVariants}
                  className="group rounded-2xl border border-neutral-200 dark:border-neutral-800 p-8 hover:border-violet-200 dark:hover:border-violet-800 hover:shadow-xl hover:shadow-violet-500/10 hover:-translate-y-1 transition-all duration-300 bg-white dark:bg-neutral-900"
                >
                  <div
                    className={`h-12 w-12 rounded-2xl bg-gradient-to-br ${gradient} flex items-center justify-center mb-5 shadow-lg ${shadow}`}
                  >
                    <Icon className="h-6 w-6 text-white" />
                  </div>
                  <h3
                    className="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2"
                    style={{ fontFamily: 'Sora, sans-serif' }}
                  >
                    {title}
                  </h3>
                  <p className="text-neutral-500 dark:text-neutral-400 text-sm leading-relaxed">{desc}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ── Section 7: CTA ──────────────────────────────────────── */}
        <section className="relative overflow-hidden py-24 px-4">
          {/* Background layers */}
          <div className="absolute inset-0 bg-gradient-to-br from-violet-600 via-violet-700 to-indigo-800" />
          <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full bg-white/5 blur-3xl" />
          <div className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full bg-cyan-500/10 blur-3xl" />

          <div className="relative z-10 container max-w-3xl mx-auto text-center">
            <FadeUp>
              {/* Eyebrow */}
              <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-sm font-medium text-white/80 mb-8">
                <Sparkles className="h-3.5 w-3.5 text-cyan-300" />
                Free to use, forever
              </div>

              <h2
                className="text-4xl md:text-6xl font-bold text-white leading-tight mb-6"
                style={{ fontFamily: 'Sora, sans-serif' }}
              >
                Your next internship is
                <br />
                one upload away
              </h2>

              <p className="text-xl text-white/70 mb-10 max-w-xl mx-auto">
                Join thousands of students who found internships that actually fit their
                skills — not just their keywords.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <button
                  onClick={() => navigate('/find')}
                  className="bg-white text-violet-700 hover:bg-violet-50 rounded-full px-8 py-4 text-base font-semibold shadow-xl hover:-translate-y-0.5 transition-all inline-flex items-center justify-center gap-2"
                >
                  <Sparkles className="h-4 w-4" />
                  Upload Your Resume
                </button>
                <button
                  onClick={() =>
                    document
                      .getElementById('how-it-works')
                      ?.scrollIntoView({ behavior: 'smooth' })
                  }
                  className="border-2 border-white/30 text-white hover:bg-white/10 rounded-full px-8 py-4 text-base font-medium transition-all"
                >
                  See How It Works
                </button>
              </div>
            </FadeUp>
          </div>
        </section>

        {/* ── Footer ──────────────────────────────────────────────── */}
        <footer className="border-t border-neutral-200 dark:border-neutral-800 py-8 px-4">
          <div className="container max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-neutral-500 dark:text-neutral-400">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-md bg-gradient-to-br from-violet-600 to-cyan-500 flex items-center justify-center">
                <Sparkles className="h-3 w-3 text-white" />
              </div>
              <span
                className="font-medium text-neutral-700 dark:text-neutral-200"
                style={{ fontFamily: 'Sora, sans-serif' }}
              >
                internshipmatcher
                <span className="text-cyan-500 text-xs align-super font-bold">AI</span>
              </span>
            </div>
            <p className="text-neutral-400">© 2025 internshipmatcher AI. Free to use, always.</p>
            <div className="flex items-center gap-5">
              <button type="button" className="hover:text-neutral-800 dark:hover:text-neutral-200 transition-colors">
                Privacy
              </button>
              <button type="button" className="hover:text-neutral-800 dark:hover:text-neutral-200 transition-colors">
                Terms
              </button>
              <button type="button" className="hover:text-neutral-800 dark:hover:text-neutral-200 transition-colors">
                Contact
              </button>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
};

export default LandingPage;
