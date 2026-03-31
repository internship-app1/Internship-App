import React, { useEffect, useState } from 'react';
import { useAuth, SignInButton } from '@clerk/react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import JobCard from '../components/JobCard';
import { Job } from '../types';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Clock, ChevronDown, ChevronUp, Sparkles, Upload } from 'lucide-react';

const getApiBaseUrl = (): string => {
  if (typeof window !== 'undefined') {
    const { hostname } = window.location;
    const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
    if (isLocalhost) {
      return (process.env.REACT_APP_API_URL ?? 'http://localhost:8000').replace(/\/+$/, '');
    }
    return '';
  }
  return process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '';
};

const API_BASE_URL = getApiBaseUrl();

interface HistoryEntry {
  id: number;
  resume_hash: string;
  results: Job[];
  skills: string[];
  created_at: string;
  expires_at: string;
}

const HistoryPage: React.FC = () => {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;

    const fetchHistory = async () => {
      setLoading(true);
      setError('');
      try {
        const token = await getToken();
        const res = await fetch(`${API_BASE_URL}/api/user-history`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`Server error ${res.status}`);
        const data: HistoryEntry[] = await res.json();
        setHistory(data);
      } catch (e: any) {
        setError(e.message ?? 'Failed to load history.');
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [isLoaded, isSignedIn, getToken]);

  const formatDate = (iso: string) => {
    // Backend returns UTC timestamps without a timezone suffix — append Z so
    // the browser correctly interprets them as UTC before converting to local.
    const normalized = iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z';
    return new Date(normalized).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const isExpired = (expires_at: string) => new Date(expires_at) < new Date();

  const analysisLabel = (hash: string) =>
    hash.endsWith('_deep') ? 'Think Deeper' : 'Quick';

  // ── Not loaded yet ──────────────────────────────────────────────────────────
  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
        <Header forceSolid />
        <div className="flex items-center justify-center h-64">
          <div className="h-8 w-8 rounded-full border-4 border-violet-500 border-t-transparent animate-spin" />
        </div>
      </div>
    );
  }

  // ── Not signed in ──────────────────────────────────────────────────────────
  if (!isSignedIn) {
    return (
      <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
        <Header forceSolid />
        <div className="max-w-lg mx-auto px-6 py-24 text-center">
          <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-violet-600 to-cyan-500 flex items-center justify-center mx-auto mb-6">
            <Sparkles className="h-7 w-7 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-neutral-950 dark:text-neutral-50 mb-3">
            Sign in to see your history
          </h2>
          <p className="text-neutral-500 dark:text-neutral-400 mb-8">
            Your past resume analyses are saved to your account so you never
            have to re-upload.
          </p>
          <SignInButton mode="modal">
            <button className="bg-violet-600 hover:bg-violet-700 text-white rounded-full px-7 py-3 text-sm font-semibold shadow-md shadow-violet-500/25 hover:shadow-violet-500/40 hover:-translate-y-0.5 transition-all">
              Sign In
            </button>
          </SignInButton>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      <Header forceSolid />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Page header */}
        <div className="mb-10">
          <h1 className="text-2xl sm:text-3xl font-bold text-neutral-950 dark:text-neutral-50 mb-2">
            Past Analyses
          </h1>
          <p className="text-neutral-500 dark:text-neutral-400">
            All your previous resume scans — click any entry to see its matched
            jobs.
          </p>
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center h-40">
            <div className="h-8 w-8 rounded-full border-4 border-violet-500 border-t-transparent animate-spin" />
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <Card className="border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/30">
            <CardContent className="py-6 text-sm text-red-600 dark:text-red-400">
              {error}
            </CardContent>
          </Card>
        )}

        {/* Empty state */}
        {!loading && !error && history.length === 0 && (
          <div className="text-center py-24">
            <Upload className="h-12 w-12 text-neutral-300 dark:text-neutral-700 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-neutral-700 dark:text-neutral-300 mb-2">
              No analyses yet
            </h3>
            <p className="text-neutral-500 dark:text-neutral-400 mb-6 text-sm">
              Upload your resume on the Find page and your results will be saved
              here automatically.
            </p>
            <Link to="/find">
              <Button className="bg-violet-600 hover:bg-violet-700 text-white rounded-full px-6">
                Upload Resume
              </Button>
            </Link>
          </div>
        )}

        {/* History list */}
        {!loading && !error && history.length > 0 && (
          <div className="space-y-4">
            {history.map((entry) => {
              const expanded = expandedId === entry.id;
              const expired = isExpired(entry.expires_at);
              const mode = analysisLabel(entry.resume_hash);

              return (
                <Card
                  key={entry.id}
                  className="border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-sm"
                >
                  {/* Row header — always visible */}
                  <CardHeader
                    className="cursor-pointer select-none"
                    onClick={() => setExpandedId(expanded ? null : entry.id)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex flex-col gap-1.5 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <CardTitle className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
                            {entry.results.length} job
                            {entry.results.length !== 1 ? 's' : ''} matched
                          </CardTitle>
                          <Badge
                            variant="secondary"
                            className={
                              mode === 'Think Deeper'
                                ? 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300 text-xs'
                                : 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300 text-xs'
                            }
                          >
                            {mode}
                          </Badge>
                          {expired && (
                            <Badge
                              variant="secondary"
                              className="bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400 text-xs"
                            >
                              Cache expired
                            </Badge>
                          )}
                        </div>

                        {/* Skills */}
                        {entry.skills.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-1">
                            {entry.skills.slice(0, 8).map((s) => (
                              <span
                                key={s}
                                className="text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 rounded-full px-2 py-0.5"
                              >
                                {s}
                              </span>
                            ))}
                            {entry.skills.length > 8 && (
                              <span className="text-xs text-neutral-400 dark:text-neutral-500 px-1 py-0.5">
                                +{entry.skills.length - 8} more
                              </span>
                            )}
                          </div>
                        )}

                        {/* Timestamp */}
                        <div className="flex items-center gap-1 text-xs text-neutral-400 dark:text-neutral-500 mt-0.5">
                          <Clock className="h-3 w-3" />
                          {formatDate(entry.created_at)}
                        </div>
                      </div>

                      <div className="text-neutral-400 dark:text-neutral-600 pt-1 shrink-0">
                        {expanded ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </div>
                    </div>
                  </CardHeader>

                  {/* Expanded job list */}
                  {expanded && (
                    <CardContent className="pt-0 pb-4 space-y-3">
                      <div className="border-t border-neutral-100 dark:border-neutral-800 pt-4">
                        {entry.results.length === 0 ? (
                          <p className="text-sm text-neutral-500 dark:text-neutral-400 text-center py-4">
                            No job matches were stored for this analysis.
                          </p>
                        ) : (
                          entry.results.map((job, idx) => (
                            <JobCard key={idx} job={job} />
                          ))
                        )}
                      </div>
                    </CardContent>
                  )}
                </Card>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
};

export default HistoryPage;
