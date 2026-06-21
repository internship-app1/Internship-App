import React from 'react';

export function BuilderBlock({ activeJobs }: { activeJobs: number | null }) {
  const indexLabel = activeJobs != null ? `${activeJobs.toLocaleString()} postings` : '— postings';
  const STAMP = [
    { k: 'stack',   v: 'python · fastapi · react' },
    { k: 'index',   v: indexLabel },
    { k: 'users',   v: '~100 students' },
    { k: 'cost',    v: '$0 · open source' },
    { k: 'refresh', v: 'every 6h' },
  ];

  return (
    <section className="py-14 border-b border-lp-border">
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_200px] gap-10 lg:gap-16 items-start">
        {/* Left: signature */}
        <div>
          {/* Kicker */}
          <div className="flex items-center gap-3 mb-6">
            <span className="block w-8 h-px bg-text-tertiary flex-shrink-0" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-text-secondary">
              The builder
            </span>
          </div>

          <p className="font-serif text-xl text-text-primary leading-[1.55] mb-6 max-w-xl">
            I built this because I was tired of firing off 50 applications a week with no clue if I had a shot. Now I know before I hit apply.
          </p>

          <div className="font-mono text-[11px] text-text-secondary mb-4 leading-relaxed">
            <strong className="text-text-primary font-semibold">
              Sujan Nandikol Sunilkumar
            </strong>
            {' · '}CS + Linguistics @ SJSU{' · '}prev. full-stack @ Burnt (YC S25)
          </div>

          <div className="flex gap-1 font-mono text-[11px] text-text-secondary items-center">
            <a
              href="https://github.com/Sujan30"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-text-primary transition-colors"
            >
              github
            </a>
            <span className="mx-1.5">·</span>
            <a
              href="https://suqjan.com"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-text-primary transition-colors"
            >
              portfolio
            </a>
            <span className="mx-1.5">·</span>
            <a
              href="https://tiktok.com/@suqjan"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-text-primary transition-colors"
            >
              tiktok @suqjan
            </a>
          </div>
        </div>

        {/* Right: stamp table */}
        <div className="border border-lp-border p-4 self-start">
          {STAMP.map(({ k, v }, i) => (
            <div
              key={k}
              className={`flex gap-3 py-2 ${i < STAMP.length - 1 ? 'border-b border-lp-border' : ''}`}
            >
              <span className="font-mono text-[10px] uppercase text-text-tertiary w-14 flex-shrink-0 tracking-wide">
                {k}
              </span>
              <span className="font-mono text-[10px] text-text-secondary">{v}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
