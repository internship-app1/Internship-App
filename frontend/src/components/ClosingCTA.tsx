export function ClosingCTA() {
  return (
    <section className="py-20 text-center border-t border-lp-border">
      <h2 className="font-serif italic text-2xl md:text-3xl text-text-primary mb-3">
        Upload your resume. See your top 10 matches in 30 seconds.
      </h2>
      <p className="text-sm text-text-secondary mb-6 max-w-md mx-auto leading-relaxed">
        Free, no signup to try. Open-source on GitHub. Built by a student, used by ~100 students.
      </p>
      <a
        href="/find"
        className="inline-flex items-center gap-2 bg-ia text-bg px-5 py-2.5 rounded-lg text-sm font-semibold hover:bg-ia-hover transition-colors"
      >
        Upload resume →
      </a>
    </section>
  );
}
