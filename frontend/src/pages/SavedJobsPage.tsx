import React, { useEffect, useMemo, useState } from 'react';
import { SignInButton, useAuth } from '@clerk/react';
import { Link } from 'react-router-dom';
import { Bookmark, CalendarDays, Upload } from 'lucide-react';
import Header from '../components/Header';
import JobCard from '../components/JobCard';
import { API_BASE_URL } from '../lib/api';
import { SavedJob, SavedJobStatus } from '../types';

const STATUS_OPTIONS: { value: SavedJobStatus; label: string }[] = [
  { value: 'saved', label: 'Saved' },
  { value: 'interested', label: 'Interested' },
  { value: 'applied', label: 'Applied' },
  { value: 'interviewing', label: 'Interviewing' },
  { value: 'offer', label: 'Offer' },
  { value: 'rejected', label: 'Rejected' },
];

const SavedJobsPage: React.FC = () => {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const [token, setToken] = useState<string | null>(null);
  const [savedJobs, setSavedJobs] = useState<SavedJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | SavedJobStatus>('all');

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;

    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const authToken = await getToken();
        setToken(authToken);
        const res = await fetch(`${API_BASE_URL}/api/saved-jobs`, {
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
        });
        if (!res.ok) throw new Error(`Server error ${res.status}`);
        const data = await res.json();
        setSavedJobs(Array.isArray(data) ? data : []);
      } catch (e: any) {
        setError(e.message || 'Failed to load saved jobs.');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [isLoaded, isSignedIn, getToken]);

  const filteredJobs = useMemo(() => {
    if (statusFilter === 'all') return savedJobs;
    return savedJobs.filter(saved => saved.status === statusFilter);
  }, [savedJobs, statusFilter]);

  const handleSavedChange = (jobHash: string, saved: boolean) => {
    if (!saved) {
      setSavedJobs(prev => prev.filter(row => row.job_hash !== jobHash));
    }
  };

  const updateSavedJob = async (row: SavedJob, patch: Partial<Pick<SavedJob, 'status' | 'notes' | 'deadline'>>) => {
    if (!token) return;
    const next = { ...row, ...patch };
    setSavedJobs(prev => prev.map(item => item.job_hash === row.job_hash ? next : item));
    try {
      const res = await fetch(`${API_BASE_URL}/api/saved-jobs/${row.job_hash}`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(patch),
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const saved = await res.json();
      setSavedJobs(prev => prev.map(item => item.job_hash === row.job_hash ? saved : item));
    } catch (e: any) {
      setError(e.message || 'Failed to update saved job.');
      setSavedJobs(prev => prev.map(item => item.job_hash === row.job_hash ? row : item));
    }
  };

  const formatDate = (iso?: string | null) => {
    if (!iso) return '';
    const normalized = iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z';
    return new Date(normalized).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-bg text-text-primary">
        <Header />
        <div className="flex items-center justify-center h-64">
          <div className="h-8 w-8 border-2 border-text-primary border-t-transparent animate-spin" />
        </div>
      </div>
    );
  }

  if (!isSignedIn) {
    return (
      <div className="min-h-screen bg-bg text-text-primary">
        <Header />
        <main className="max-w-[860px] mx-auto px-6 py-24">
          <Bookmark className="h-8 w-8 text-text-tertiary mb-6" />
          <h1 className="font-serif text-3xl text-text-primary mb-3">Save jobs as you compare them.</h1>
          <p className="font-mono text-xs text-text-tertiary mb-8 max-w-sm">
            Sign in to keep a private application tracker across analyses.
          </p>
          <SignInButton mode="modal">
            <button className="inline-block bg-text-primary text-bg px-5 py-2.5 font-mono text-xs tracking-wide hover:opacity-80 transition-opacity focus:outline-none focus-visible:ring-2 focus-visible:ring-text-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg">
              Sign in →
            </button>
          </SignInButton>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg text-text-primary">
      <Header />

      <main className="max-w-[860px] mx-auto px-6 py-12">
        <div className="mb-8 pb-6 border-b border-lp-border">
          <div className="flex flex-col gap-2 mb-4">
            <span className="block w-8 h-px bg-text-tertiary" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-text-secondary">
              Application tracker
            </span>
          </div>
          <h1 className="font-serif text-3xl text-text-primary">Saved jobs.</h1>
          <p className="font-mono text-xs text-text-tertiary mt-2">
            Track status, notes, and deadlines for roles you want to pursue.
          </p>
        </div>

        {loading && (
          <div className="flex items-center justify-center h-40">
            <div className="h-8 w-8 border-2 border-text-primary border-t-transparent animate-spin" />
          </div>
        )}

        {!loading && error && (
          <div className="border border-red-500/40 bg-red-500/5 p-4 mb-6">
            <p className="font-mono text-xs text-red-500">{error}</p>
          </div>
        )}

        {!loading && savedJobs.length === 0 && (
          <div className="py-20">
            <Upload className="h-8 w-8 text-text-tertiary mb-6" />
            <h2 className="font-serif text-2xl text-text-primary mb-2">No saved jobs yet.</h2>
            <p className="font-mono text-xs text-text-tertiary mb-8 max-w-md">
              Run a match, save the roles you care about, then manage your application list here.
            </p>
            <Link
              to="/find"
              className="inline-block bg-text-primary text-bg px-5 py-2.5 font-mono text-xs tracking-wide hover:opacity-80 transition-opacity focus:outline-none focus-visible:ring-2 focus-visible:ring-text-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
            >
              Find matches →
            </Link>
          </div>
        )}

        {!loading && savedJobs.length > 0 && (
          <>
            <div className="flex items-center gap-2 flex-wrap pb-5 border-b border-lp-border">
              <button
                onClick={() => setStatusFilter('all')}
                className={`font-mono text-xs px-2 py-1 border transition-colors ${statusFilter === 'all' ? 'border-text-primary text-text-primary' : 'border-lp-border text-text-secondary hover:text-text-primary'}`}
              >
                All ({savedJobs.length})
              </button>
              {STATUS_OPTIONS.map(option => {
                const count = savedJobs.filter(row => row.status === option.value).length;
                return (
                  <button
                    key={option.value}
                    onClick={() => setStatusFilter(option.value)}
                    className={`font-mono text-xs px-2 py-1 border transition-colors ${statusFilter === option.value ? 'border-text-primary text-text-primary' : 'border-lp-border text-text-secondary hover:text-text-primary'}`}
                  >
                    {option.label} ({count})
                  </button>
                );
              })}
            </div>

            <div className="divide-y divide-lp-border">
              {filteredJobs.map(row => (
                <div key={row.job_hash} className="py-5">
                  {row.job ? (
                    <JobCard
                      job={row.job}
                      apiBaseUrl={API_BASE_URL}
                      authToken={token}
                      isSaved
                      onSavedChange={handleSavedChange}
                    />
                  ) : (
                    <div className="border border-lp-border bg-surface p-5">
                      <p className="font-mono text-xs text-text-secondary">This job is no longer in the jobs database.</p>
                    </div>
                  )}

                  <div className="mt-3 border border-lp-border bg-surface p-4 grid gap-3 md:grid-cols-[180px_1fr_180px]">
                    <label className="flex flex-col gap-1">
                      <span className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary">Status</span>
                      <select
                        value={row.status}
                        onChange={e => updateSavedJob(row, { status: e.target.value as SavedJobStatus })}
                        className="bg-bg border border-lp-border px-2 py-2 text-sm text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-text-primary"
                      >
                        {STATUS_OPTIONS.map(option => (
                          <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                      </select>
                    </label>

                    <label className="flex flex-col gap-1">
                      <span className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary">Notes</span>
                      <textarea
                        value={row.notes}
                        onChange={e => updateSavedJob(row, { notes: e.target.value })}
                        rows={2}
                        className="bg-bg border border-lp-border px-2 py-2 text-sm text-text-primary resize-none focus:outline-none focus-visible:ring-2 focus-visible:ring-text-primary"
                        placeholder="Recruiter name, application context, follow-up..."
                      />
                    </label>

                    <label className="flex flex-col gap-1">
                      <span className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary">Deadline</span>
                      <input
                        type="date"
                        value={row.deadline || ''}
                        onChange={e => updateSavedJob(row, { deadline: e.target.value })}
                        className="bg-bg border border-lp-border px-2 py-2 text-sm text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-text-primary"
                      />
                      {row.applied_at && (
                        <span className="font-mono text-[10px] text-text-tertiary inline-flex items-center gap-1">
                          <CalendarDays className="h-3 w-3" />
                          Applied {formatDate(row.applied_at)}
                        </span>
                      )}
                    </label>
                  </div>
                </div>
              ))}
            </div>

            {filteredJobs.length === 0 && (
              <div className="py-16 text-center border-b border-lp-border">
                <p className="font-mono text-xs text-text-tertiary">No saved jobs in this status.</p>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
};

export default SavedJobsPage;
