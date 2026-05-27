const DETECTED_SKILLS = ['Python', 'React', 'TypeScript', 'SQL', 'FastAPI', 'Git', 'REST APIs'];

const SAMPLE_RESULTS = [
  {
    rank: 1,
    title: 'Software Engineer Intern',
    company: 'Ramp',
    location: 'New York, NY',
    term: 'Summer 2026',
    score: 94,
    matched: ['Python', 'React', 'TypeScript', 'REST APIs'],
    gaps: ['Go'],
    reasoning:
      'Strong match — your React and Python experience maps directly to their fintech stack. 4 of 5 required skills detected.',
    isNew: true,
  },
  {
    rank: 2,
    title: 'Backend Engineer Intern',
    company: 'Linear',
    location: 'Remote',
    term: 'Summer 2026',
    score: 88,
    matched: ['Python', 'FastAPI', 'SQL'],
    gaps: ['Rust'],
    reasoning:
      'Solid backend fit. FastAPI and Postgres match their API layer. Missing systems-level experience but not required for intern role.',
    isNew: false,
  },
  {
    rank: 3,
    title: 'Full Stack Intern',
    company: 'Vercel',
    location: 'Remote',
    term: 'Summer 2026',
    score: 81,
    matched: ['React', 'TypeScript'],
    gaps: ['Next.js', 'Edge Functions'],
    reasoning:
      'Frontend skills align well. Next.js experience would strengthen the fit — worth applying if you can show React depth.',
    isNew: false,
  },
];

function ScoreBar({ score }: { score: number }) {
  const color =
    score >= 90 ? 'bg-emerald-400' : score >= 80 ? 'bg-ia' : 'bg-slate-400';
  return (
    <div className="w-full h-0.5 bg-lp-border rounded-full overflow-hidden mt-1.5">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
    </div>
  );
}

export function ResultsPreview() {
  return (
    <div className="bg-surface rounded-lg border border-lp-border overflow-hidden text-sm select-none">
      {/* Skills strip */}
      <div className="px-4 py-3 border-b border-lp-border flex flex-wrap items-center gap-2">
        <span className="text-[11px] text-text-tertiary font-medium shrink-0">
          Skills detected:
        </span>
        {DETECTED_SKILLS.map((s) => (
          <span
            key={s}
            className="text-[10px] px-1.5 py-0.5 bg-ia-subtle text-ia-pill rounded font-mono"
          >
            {s}
          </span>
        ))}
      </div>

      {/* Results list */}
      <div className="divide-y divide-lp-border">
        {SAMPLE_RESULTS.map((job, i) => (
          <div key={job.company} className="px-4 py-3.5 group relative">
            {/* Annotation pin — only on first card */}
            {i === 0 && (
              <span className="absolute -right-0 top-3.5 hidden lg:flex items-center gap-1.5 text-[10px] text-text-tertiary pr-4">
                <span className="w-4 h-4 rounded-full bg-ia text-bg flex items-center justify-center font-bold text-[9px] shrink-0">
                  1
                </span>
                Match score
              </span>
            )}

            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className="text-[10px] text-text-tertiary font-mono">#{job.rank}</span>
                  <span className="text-[11px] font-semibold text-text-primary truncate">
                    {job.title}
                  </span>
                </div>
                <div className="text-[11px] text-text-secondary">
                  {job.company} · {job.location} · {job.term}
                </div>
              </div>

              <div className="shrink-0 text-right">
                <div
                  className={`font-serif italic text-xl leading-none ${
                    job.score >= 90
                      ? 'text-emerald-400'
                      : job.score >= 80
                      ? 'text-ia'
                      : 'text-text-secondary'
                  }`}
                >
                  {job.score}%
                </div>
                <ScoreBar score={job.score} />
              </div>
            </div>

            {/* Skills row with annotation on second card */}
            <div className="flex flex-wrap gap-1 mt-2 relative">
              {i === 1 && (
                <span className="absolute -left-0 -top-5 hidden lg:flex items-center gap-1.5 text-[10px] text-text-tertiary">
                  <span className="w-4 h-4 rounded-full bg-ia text-bg flex items-center justify-center font-bold text-[9px] shrink-0">
                    2
                  </span>
                  Matched skills
                </span>
              )}
              {job.matched.map((s) => (
                <span
                  key={s}
                  className="text-[10px] px-1.5 py-0.5 bg-ia-subtle text-ia-pill rounded font-mono"
                >
                  {s}
                </span>
              ))}
              {job.gaps.map((s) => (
                <span
                  key={s}
                  className="text-[10px] px-1.5 py-0.5 bg-surface text-text-tertiary rounded font-mono border border-lp-border"
                >
                  {s}
                </span>
              ))}
              {job.isNew && (
                <span className="text-[10px] px-1.5 py-0.5 bg-emerald-950/50 text-emerald-400 rounded ml-auto">
                  NEW
                </span>
              )}
            </div>

            <p className="text-[11px] text-text-secondary leading-relaxed mt-2">
              {job.reasoning}
            </p>
          </div>
        ))}
      </div>

      {/* Footer strip */}
      <div className="px-4 py-2.5 border-t border-lp-border flex items-center justify-between">
        <span className="text-[10px] text-text-tertiary">
          Showing 3 of 10 matches · sorted by compatibility
        </span>
        <a
          href="/find"
          className="text-[10px] text-ia hover:text-ia-hover transition-colors font-medium"
        >
          See your matches →
        </a>
      </div>
    </div>
  );
}
