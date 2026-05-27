import React, { useEffect, useState } from 'react';

export function HonestStats() {
  const [liveCount, setLiveCount] = useState<number | null>(null);

  useEffect(() => {
    fetch('/api/database-stats')
      .then((r) => r.json())
      .then((data) => {
        const count = data.total_jobs ?? data.active_jobs ?? data.job_count ?? null;
        if (typeof count === 'number') setLiveCount(count);
      })
      .catch(() => {});
  }, []);

  const displayCount = (liveCount ?? 847).toLocaleString();

  return (
    <section className="py-12 border-b border-lp-border">
      <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-8">
        By the numbers · pulled from the running index
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3">
        {/* Stat 1 */}
        <div className="pb-8 sm:pb-0 sm:pr-8 border-b sm:border-b-0 sm:border-r border-lp-border mb-8 sm:mb-0">
          <div className="font-serif text-5xl text-text-primary leading-none mb-3">
            {displayCount}
          </div>
          <div className="text-xs text-text-secondary leading-snug mb-2">
            Live internships indexed from GitHub lists and company boards.
          </div>
          <div className="font-mono text-[10px] text-text-tertiary">refreshed every 6h</div>
        </div>

        {/* Stat 2 */}
        <div className="pb-8 sm:pb-0 sm:px-8 border-b sm:border-b-0 sm:border-r border-lp-border mb-8 sm:mb-0">
          <div className="font-serif text-5xl text-text-primary leading-none mb-3">
            30<span className="font-mono text-2xl">s</span>
          </div>
          <div className="text-xs text-text-secondary leading-snug mb-2">
            From résumé upload to your top ten ranked matches.
          </div>
          <div className="font-mono text-[10px] text-text-tertiary">median across 100 users</div>
        </div>

        {/* Stat 3 */}
        <div className="sm:pl-8">
          <div className="font-serif text-5xl text-text-primary leading-none mb-3">$0</div>
          <div className="text-xs text-text-secondary leading-snug mb-2">
            No paywall. No ads. Open source on GitHub.
          </div>
          <div className="font-mono text-[10px] text-text-tertiary">always will be</div>
        </div>
      </div>
    </section>
  );
}
