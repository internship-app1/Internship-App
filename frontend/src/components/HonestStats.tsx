import heroData from '../data/landing-hero.json';

export function HonestStats() {
  const { indexCount, hoursAgo } = heroData;

  const stats = [
    {
      value: indexCount.toLocaleString(),
      label: 'Live internships indexed from GitHub lists + company boards',
    },
    {
      value: '~30s',
      label: 'From resume upload to your top 10 ranked matches',
      highlight: true,
    },
    {
      value: '$0',
      label: 'No paywall · no ads · open-source on GitHub',
    },
  ];

  return (
    <section className="py-10 border-t border-lp-border">
      <div className="flex items-center gap-2 text-xs text-ia mb-4">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        <span>Index live · last refreshed {hoursAgo}h ago</span>
      </div>

      <div className="grid grid-cols-3 border-t border-lp-border pt-4">
        {stats.map((s, i) => (
          <div
            key={s.label}
            className={[
              'px-4',
              i !== 0 ? 'border-l border-lp-border' : 'pl-0',
              i === 2 ? 'pr-0' : '',
            ].join(' ')}
          >
            <div className="font-serif italic text-2xl md:text-3xl text-text-primary leading-none mb-2">
              {s.highlight ? (
                <em className="text-ia not-italic">{s.value}</em>
              ) : (
                s.value
              )}
            </div>
            <div className="text-xs text-text-secondary leading-snug">{s.label}</div>
          </div>
        ))}
      </div>

      <p className="text-xs text-text-tertiary mt-4">
        <span className="text-emerald-400">●</span> Refreshes daily. Numbers pulled from the
        running index — not marketing copy.
      </p>
    </section>
  );
}
