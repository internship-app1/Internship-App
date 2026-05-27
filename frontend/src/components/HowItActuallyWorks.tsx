export function HowItActuallyWorks() {
  return (
    <section className="py-16 border-t border-lp-border">
      <h2 className="text-base font-semibold text-text-primary mb-2">How it actually works</h2>
      <p className="text-sm text-text-secondary mb-6 max-w-xl leading-relaxed">
        Upload a PDF resume. We extract skills, frameworks, and experience levels — then rank every
        live posting against your profile in under 30 seconds.
      </p>

      <figure className="relative rounded-lg overflow-hidden border border-lp-border bg-surface">
        <img
          src="/screenshots/matcher-results.png"
          alt="Screenshot of the matcher results page showing ranked internships with match scores and skill overlaps"
          className="w-full"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = 'none';
            const placeholder = document.getElementById('screenshot-placeholder');
            if (placeholder) placeholder.style.display = 'flex';
          }}
        />
        {/* Placeholder shown before screenshot is captured */}
        <div
          id="screenshot-placeholder"
          className="hidden w-full py-24 items-center justify-center text-center"
        >
          <div>
            <p className="text-sm font-semibold text-text-primary mb-1">Screenshot coming soon</p>
            <p className="text-xs text-text-tertiary">
              Try the matcher at{' '}
              <a href="/find" className="text-ia hover:text-ia-hover transition-colors">
                /find
              </a>{' '}
              to see it in action
            </p>
          </div>
        </div>
      </figure>

      <p className="text-xs text-text-tertiary mt-3">
        Real screenshot from the live app. No mockups, no illustrations.
      </p>
    </section>
  );
}
