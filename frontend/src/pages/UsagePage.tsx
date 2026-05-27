import React from 'react';
import { useAuth, SignInButton } from '@clerk/react';
import Header from '../components/Header';
import { useUsage } from '../hooks/useUsage';

function formatReset(resetAt: string | null): string {
  if (!resetAt) return '—';
  const normalized = resetAt.endsWith('Z') || resetAt.includes('+') ? resetAt : resetAt + 'Z';
  const date = new Date(normalized);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / 86400000);

  const abs = date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });

  if (diffDays <= 0) return `today · ${abs}`;
  if (diffDays === 1) return `tomorrow · ${abs}`;
  return `in ${diffDays} days · ${abs}`;
}

const UsagePage: React.FC = () => {
  const { isLoaded, isSignedIn } = useAuth();
  const { data, loading, error } = useUsage();

  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-bg text-text-primary">
        <Header forceSolid />
        <div className="flex items-center justify-center h-64">
          <div className="h-8 w-8 border-2 border-text-primary border-t-transparent animate-spin" />
        </div>
      </div>
    );
  }

  if (!isSignedIn) {
    return (
      <div className="min-h-screen bg-bg text-text-primary">
        <Header forceSolid />
        <div className="max-w-[860px] mx-auto px-6 py-24">
          <div className="flex flex-col gap-2 mb-6">
            <span className="block w-8 h-px bg-text-tertiary" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-text-secondary">
              Sign in required
            </span>
          </div>
          <h2 className="font-serif text-3xl text-text-primary mb-3">
            Sign in to view your usage.
          </h2>
          <p className="font-mono text-xs text-text-tertiary mb-8 max-w-sm">
            Your weekly quotas are tied to your account.
          </p>
          <SignInButton mode="modal">
            <button className="inline-block bg-text-primary text-bg px-5 py-2.5 font-mono text-xs tracking-wide hover:opacity-80 transition-opacity focus:outline-none focus-visible:ring-2 focus-visible:ring-text-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg">
              Sign in →
            </button>
          </SignInButton>
        </div>
      </div>
    );
  }

  const tr = data?.tailor_resume;
  const pct = tr ? Math.min((tr.used / tr.limit) * 100, 100) : 0;
  const atLimit = tr ? tr.remaining === 0 : false;

  return (
    <div className="min-h-screen bg-bg text-text-primary">
      <Header forceSolid />
      <main className="max-w-[860px] mx-auto px-6 py-12">
        {/* Page header */}
        <div className="mb-10 pb-6 border-b border-lp-border">
          <div className="flex flex-col gap-2 mb-4">
            <span className="block w-8 h-px bg-text-tertiary" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-text-secondary">
              Account / Usage
            </span>
          </div>
          <h1 className="font-serif text-3xl text-text-primary">Your usage.</h1>
          <p className="font-mono text-xs text-text-tertiary mt-2">
            Tracked weekly. Resets every seven days from your first request.
          </p>
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center h-40">
            <div className="h-8 w-8 border-2 border-text-primary border-t-transparent animate-spin" />
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="border border-lp-border bg-surface p-5">
            <p className="font-mono text-xs text-text-secondary">{error}</p>
          </div>
        )}

        {/* Usage card */}
        {!loading && !error && tr && (
          <div className="flex flex-col gap-4">
            {/* Primary meter card */}
            <div className="border border-lp-border bg-surface p-6">
              <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-4">
                Tailored resumes
              </div>

              {/* Counter */}
              <div className="flex items-baseline gap-1.5 mb-5">
                <span className={`font-serif text-4xl leading-none ${atLimit ? 'text-red-500' : 'text-text-primary'}`}>
                  {tr.used}
                </span>
                <span className="font-mono text-sm text-text-tertiary">/ {tr.limit}</span>
              </div>

              {/* Progress bar */}
              <div className="w-full h-px bg-lp-border mb-5 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${atLimit ? 'bg-red-500' : 'bg-text-primary'}`}
                  style={{ width: `${pct}%` }}
                />
              </div>

              {/* Three-column metadata */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-1">
                    Used
                  </div>
                  <div className="font-serif text-lg text-text-primary leading-none">{tr.used}</div>
                </div>
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-1">
                    Remaining
                  </div>
                  <div className={`font-serif text-lg leading-none ${atLimit ? 'text-red-500' : 'text-text-primary'}`}>
                    {tr.remaining}
                  </div>
                </div>
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-1">
                    Renews
                  </div>
                  <div className="font-mono text-xs text-text-secondary leading-snug">
                    {formatReset(tr.reset_at)}
                  </div>
                </div>
              </div>
            </div>

            {/* Explainer card */}
            <div className="border border-lp-border bg-surface p-6">
              <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-3">
                About this limit
              </div>
              <p className="text-sm text-text-secondary leading-relaxed">
                Tailoring a resume calls a Claude Sonnet model and compiles a
                fresh LaTeX PDF — it's the most compute-heavy action in the
                app. The weekly cap of {tr.limit} keeps the lights on.
                Quick matches and Think Deeper analyses are{' '}
                <span className="font-medium text-text-primary">unlimited</span>.
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default UsagePage;
