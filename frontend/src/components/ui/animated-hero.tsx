import heroData from '../../data/landing-hero.json';

function Hero() {
  const { indexCount, hoursAgo, sampleRole } = heroData;

  return (
    <section className="py-16 md:py-24">
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-10 lg:gap-14 items-start">
        {/* Left: text */}
        <div>
          <div className="flex items-center gap-2 text-xs text-ia mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)] animate-pulse" />
            <span>{indexCount.toLocaleString()} internships indexed · updated {hoursAgo}h ago</span>
          </div>

          <h1 className="font-serif italic text-3xl md:text-4xl text-text-primary leading-[1.1] mb-4">
            Upload your resume. Get{' '}
            <span className="not-italic font-sans font-semibold text-ia">
              10 internships
            </span>{' '}
            that actually fit your skills.
          </h1>

          <p className="text-sm text-text-secondary leading-relaxed max-w-md mb-6">
            Free tool built by a CS student at SJSU. We rank live postings against what's actually
            in your resume — not keyword matching.
          </p>

          <div className="flex items-center gap-4">
            <a
              href="/find"
              className="bg-ia text-bg px-4 py-2 rounded-lg text-sm font-semibold hover:bg-ia-hover transition-colors"
            >
              Upload resume →
            </a>
            <span className="text-xs text-text-tertiary">~30s · no signup to try</span>
          </div>
        </div>

        {/* Right: real match card */}
        <div className="bg-surface border border-lp-border rounded-lg p-4 w-full">
          <div className="flex justify-between items-start mb-3">
            <div>
              <div className="text-sm font-semibold text-text-primary">{sampleRole.title}</div>
              <div className="text-xs text-text-secondary mt-0.5">
                {sampleRole.company} · {sampleRole.location} · {sampleRole.term}
              </div>
            </div>
            <div className="font-serif italic text-2xl text-emerald-400 leading-none">
              {sampleRole.score}
            </div>
          </div>

          <div className="flex gap-1.5 flex-wrap my-2.5">
            {sampleRole.matchedSkills.map((s) => (
              <span
                key={s}
                className="text-[10px] px-1.5 py-0.5 bg-ia-subtle text-ia-pill rounded"
              >
                {s}
              </span>
            ))}
          </div>

          <p className="text-[11px] text-text-secondary leading-relaxed pt-2.5 border-t border-lp-border">
            {sampleRole.explanation}
          </p>
        </div>
      </div>
    </section>
  );
}

export { Hero };
