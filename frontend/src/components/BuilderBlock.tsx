import heroData from '../data/landing-hero.json';

export function BuilderBlock() {
  const { indexCount } = heroData;

  return (
    <section className="py-12 border-t border-lp-border">
      <div className="text-[11px] tracking-widest text-ia uppercase mb-4">Who built this</div>

      <div className="grid grid-cols-1 sm:grid-cols-[80px_1fr] gap-6 items-start">
        <div className="w-20 h-20 rounded-full bg-ia-subtle border border-lp-border flex items-center justify-center font-serif italic text-4xl text-ia flex-shrink-0">
          S
        </div>

        <div>
          <p className="font-serif italic text-xl md:text-2xl text-text-primary leading-[1.35] mb-4">
            "I built this because I was sick of pasting my resume into job boards that ranked roles
            by keyword density. The matcher reads what's actually in your resume and ranks live
            postings against it — no recruiter middleware, no paywall, no ads."
          </p>

          <div className="flex flex-wrap items-baseline gap-2 mb-3">
            <span className="text-sm font-semibold text-text-primary">Sujan Nandikol Sunilkumar</span>
            <span className="text-xs text-text-secondary">
              —{' '}
              <span className="text-ia-pill font-medium">CS + Linguistics @ SJSU</span>
              {' '}· prev. full-stack @ Burnt (YC S25)
            </span>
          </div>

          <div className="flex gap-4 text-xs mb-4">
            <a
              className="text-ia hover:text-ia-hover transition-colors"
              href="https://github.com/Sujan30/jobbot"
              target="_blank"
              rel="noopener noreferrer"
            >
              github ↗
            </a>
            <a
              className="text-ia hover:text-ia-hover transition-colors"
              href="https://suqjan.com"
              target="_blank"
              rel="noopener noreferrer"
            >
              portfolio ↗
            </a>
            <a
              className="text-ia hover:text-ia-hover transition-colors"
              href="https://tiktok.com/@suqjan"
              target="_blank"
              rel="noopener noreferrer"
            >
              tiktok @suqjan ↗
            </a>
          </div>

          <div className="flex flex-wrap gap-6 pt-3 border-t border-lp-border text-xs text-text-secondary">
            <span>
              <span className="font-serif italic text-base font-medium text-text-primary">~100</span>
              {' '}active users
            </span>
            <span>
              <span className="font-serif italic text-base font-medium text-text-primary">
                {indexCount.toLocaleString()}
              </span>
              {' '}postings indexed
            </span>
            <span>
              <span className="font-serif italic text-base font-medium text-text-primary">$0</span>
              {' '}· open-source · no ads
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
