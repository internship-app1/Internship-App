import React, { useState } from 'react';
import { useUser, useAuth } from '@clerk/react';
import Header from '../components/Header';
import JobCard from '../components/JobCard';
import { Job } from '../types';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Upload, AlertCircle, Sparkles, CheckCircle2, ArrowUp, ArrowDown, ChevronLeft, ChevronRight, Clock, RefreshCcw } from 'lucide-react';
import { cn } from '../lib/utils';

// For SSE streaming, we need to bypass the CRA proxy in development
// because it buffers responses. In production, use relative URLs.
// Priority:
// 1. On localhost (dev): use REACT_APP_API_URL if set, otherwise http://localhost:8000
// 2. On any non-localhost host (prod/staging): ALWAYS use relative URLs (empty string),
//    even if REACT_APP_API_URL was accidentally baked into the bundle.
// 3. In non-browser environments: fall back to localhost in development only.
const getApiBaseUrl = (): string => {
  if (typeof window !== 'undefined') {
    const { hostname } = window.location;
    const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';

    const envUrl = process.env.REACT_APP_API_URL?.trim();

    if (isLocalhost) {
      if (envUrl) {
        // Normalize to avoid trailing slashes like "https://api.example.com/"
        return envUrl.replace(/\/+$/, '');
      }
      return 'http://localhost:8000';
    }

    // In production (or any non-localhost host), use same-origin relative URLs
    // so Nginx / reverse proxy can route /api to the backend.
    return '';
  }

  // Fallback for non-browser environments (tests, SSR, etc.)
  if (process.env.NODE_ENV === 'development') {
    return 'http://localhost:8000';
  }

  return '';
};

const API_BASE_URL = getApiBaseUrl();

const FindPage: React.FC = () => {
  const user = useUser();
  const { userId } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasResults, setHasResults] = useState(false);
  const [skillsFound, setSkillsFound] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [useStreaming, setUseStreaming] = useState(true);
  const [thinkDeeper, setThinkDeeper] = useState(true);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fromCache, setFromCache] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // Pagination and filtering state
  const [currentPage, setCurrentPage] = useState(1);
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc' | 'recent'>('desc');
  const itemsPerPage = 10;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const hashFile = async (file: File): Promise<string> => {
    if (crypto?.subtle?.digest) {
      const buffer = await file.arrayBuffer();
      const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
      return Array.from(new Uint8Array(hashBuffer))
        .map(b => b.toString(16).padStart(2, '0')).join('');
    }
    // Fallback for insecure contexts (HTTP on non-localhost) — crypto.subtle unavailable
    return `${file.name}-${file.size}-${file.lastModified}`;
  };

  const handleFileUploadStreaming = async (file: File) => {
    console.log('Starting file upload:', file.name);
    setFromCache(false);
    const resumeHash = await hashFile(file);

    if (userId) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/resume-cache/${resumeHash}?user_id=${userId}`);
        const data = await res.json();
        if (data.hit) {
          setJobs(data.results);
          setSkillsFound(data.skills);
          setHasResults(true);
          setFromCache(true);
          return; // skip full pipeline
        }
      } catch (e) {
        // cache check failed silently — fall through to full pipeline
      }
    }

    setIsLoading(true);
    setError('');
    setHasResults(false);
    setJobs([]);
    setSkillsFound([]);
    setProgress(0);
    setCurrentStep('Starting...');

    try {
      const formData = new FormData();
      formData.append('resume', file);
      formData.append('think_deeper', thinkDeeper.toString());
      formData.append('user_id', userId || '');
      formData.append('resume_hash', resumeHash);

      // Use direct backend URL to bypass CRA proxy buffering for SSE
      const response = await fetch(`${API_BASE_URL}/api/match-stream`, {
        method: 'POST',
        body: formData,
      });

      console.log('SSE Response received, starting stream processing...');

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      const processedJobs: Job[] = [];
      let buffer = ''; // Buffer for incomplete lines

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log('Stream ended');
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        const lines = buffer.split('\n');

        // Keep the last incomplete line in the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim().startsWith('data: ')) {
            try {
              const jsonStr = line.trim().slice(6); // Remove 'data: ' prefix
              const data = JSON.parse(jsonStr);

              if (data.error) {
                setError(data.error);
                setIsLoading(false);
                return;
              }

              if (data.progress !== undefined) {
                setProgress(data.progress);
              }

              if (data.message) {
                setCurrentStep(data.message);
              }

              if (data.skills) {
                setSkillsFound(data.skills);
              }

              if (data.job_result) {
                processedJobs.push(data.job_result);
                const sortedJobs = [...processedJobs].sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
                setJobs(sortedJobs);
                setHasResults(true);
              }

              if (data.complete) {
                setCurrentStep('Complete!');
                setProgress(100);
                setIsLoading(false);

                if (data.final_results && Array.isArray(data.final_results)) {
                  setJobs(data.final_results);
                  setHasResults(true);
                } else {
                  console.warn('No final_results in completion data:', data);
                }

                if (data.matches_found === 0) {
                  setError('No matching opportunities found for your skills.');
                } else if (data.total_results) {
                  console.log(`Successfully matched ${data.matches_found} jobs, showing ${data.total_results} results`);
                }
                break;
              }
            } catch (parseError) {
              console.error('Error parsing SSE data:', parseError);
            }
          }
        }
      }
    } catch (err: any) {
      console.error('Streaming error:', err);
      setError(err.message || 'An error occurred while processing your resume.');
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFile) {
      handleFileUploadStreaming(selectedFile);
    }
  };

  const handleTryAgain = () => {
    setError('');
    setHasResults(false);
    setJobs([]);
    setSkillsFound([]);
    setProgress(0);
    setCurrentStep('');
    setSelectedFile(null);
  };

  // Reset pagination when new results come in
  React.useEffect(() => {
    if (jobs.length > 0) {
      setCurrentPage(1);
    }
  }, [jobs.length]);

  // Sorting and pagination logic
  const sortedJobs = React.useMemo(() => {
    const sorted = [...jobs].sort((a, b) => {
      if (sortOrder === 'recent') {
        const dateA = a.first_seen ? new Date(a.first_seen).getTime() : 0;
        const dateB = b.first_seen ? new Date(b.first_seen).getTime() : 0;
        return dateB - dateA;
      } else {
        const scoreA = a.match_score || a.score || 0;
        const scoreB = b.match_score || b.score || 0;
        return sortOrder === 'desc' ? scoreB - scoreA : scoreA - scoreB;
      }
    });
    return sorted;
  }, [jobs, sortOrder]);

  const totalPages = Math.ceil(sortedJobs.length / itemsPerPage);

  const currentPageJobs = React.useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return sortedJobs.slice(startIndex, endIndex);
  }, [sortedJobs, currentPage, itemsPerPage]);

  const handleSortChange = (newOrder: 'desc' | 'asc' | 'recent') => {
    setSortOrder(newOrder);
    setCurrentPage(1);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    document.getElementById('results-section')?.scrollIntoView({ behavior: 'smooth' });
  };

  // Determine if error is a "no results" error vs a real error
  const isNoResultsError =
    error === 'No matching opportunities found for your skills.';

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-violet-50/20 to-neutral-50">
      <Header />

      <main className="container py-8 space-y-8">
        {/* Header Section */}
        <div className="text-center space-y-4">
          <h1
            className="text-4xl md:text-5xl font-bold tracking-tight"
            style={{ fontFamily: 'Sora, sans-serif' }}
          >
            Find Your Best-Fit Internships
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Upload your resume and get AI-matched to internships that actually fit your skills — in seconds.
          </p>
        </div>

        {/* Upload Section */}
        <Card className="max-w-2xl mx-auto shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5 text-violet-600" />
              Upload Your Resume
            </CardTitle>
            <CardDescription>
              Upload your resume (PDF or image) to get personalized internship recommendations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="flex flex-col items-center gap-4">
                {/* Drop zone */}
                <label
                  className={cn(
                    'flex flex-col items-center justify-center w-full h-36 border-2 border-dashed rounded-2xl cursor-pointer transition-all duration-200',
                    isDragging
                      ? 'border-violet-500 bg-violet-50 scale-[1.01]'
                      : selectedFile
                      ? 'border-violet-400 bg-violet-50/60'
                      : 'border-neutral-300 hover:border-violet-300 hover:bg-violet-50/30'
                  )}
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                >
                  <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    {selectedFile ? (
                      <>
                        <CheckCircle2 className="h-8 w-8 mb-2 text-violet-600" />
                        <p className="text-sm font-medium text-neutral-800">{selectedFile.name}</p>
                        <p className="text-xs text-neutral-500 mt-0.5">Click to change file</p>
                      </>
                    ) : isDragging ? (
                      <>
                        <Upload className="h-8 w-8 mb-2 text-violet-600" />
                        <p className="text-sm font-medium text-violet-700">Drop it here</p>
                      </>
                    ) : (
                      <>
                        <Upload className="h-8 w-8 mb-2 text-neutral-400" />
                        <p className="text-sm font-medium text-neutral-700">
                          Click to upload or drag and drop
                        </p>
                        <p className="text-xs text-neutral-400 mt-0.5">PDF, PNG, JPG (MAX. 10MB)</p>
                      </>
                    )}
                  </div>
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf,.png,.jpg,.jpeg"
                    onChange={handleFileChange}
                  />
                </label>

                {/* Think Deeper toggle */}
                <div className="w-full max-w-sm">
                  <div className="flex items-start gap-3 rounded-xl border border-neutral-200 bg-neutral-50/80 p-3">
                    <input
                      type="checkbox"
                      id="thinkDeeper"
                      checked={thinkDeeper}
                      onChange={(e) => setThinkDeeper(e.target.checked)}
                      className="mt-0.5 h-4 w-4 rounded border-neutral-300 accent-violet-600 cursor-pointer"
                    />
                    <div>
                      <label
                        htmlFor="thinkDeeper"
                        className="text-sm font-medium text-neutral-800 cursor-pointer"
                      >
                        Think Deeper
                      </label>
                      <p className="text-xs text-neutral-500 mt-0.5 leading-relaxed">
                        Enables deeper AI reasoning — adds skill gap analysis, red flags, and career fit.
                        Takes ~30s longer.
                      </p>
                    </div>
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full md:w-auto px-8 rounded-full bg-violet-600 hover:bg-violet-700 text-white shadow-lg shadow-violet-500/25"
                  disabled={!selectedFile || isLoading}
                >
                  {isLoading ? (
                    <>
                      <Sparkles className="h-4 w-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4 mr-2" />
                      Find Matches
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Enhanced Progress Section */}
        {isLoading && (
          <Card className="max-w-2xl mx-auto border-2 border-violet-200/60 shadow-lg shadow-violet-500/5">
            <CardContent className="pt-6 pb-6">
              <div className="space-y-5">
                {/* Progress Header */}
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="h-10 w-10 rounded-full bg-gradient-to-br from-violet-500 to-violet-700 flex items-center justify-center">
                      <Sparkles className="h-5 w-5 text-white animate-pulse" />
                    </div>
                    <div className="absolute inset-0 rounded-full bg-gradient-to-br from-violet-500 to-violet-700 animate-ping opacity-20"></div>
                  </div>
                  <div className="flex-1">
                    <p className="text-lg font-semibold text-foreground leading-tight">
                      {currentStep || 'Processing...'}
                    </p>
                    <p className="text-sm text-muted-foreground mt-0.5">
                      Please wait while we analyze your resume
                    </p>
                  </div>
                  <div className="text-right">
                    <div
                      className="text-2xl font-bold"
                      style={{
                        background: 'linear-gradient(135deg,#7C3AED,#22D3EE)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        backgroundClip: 'text',
                      }}
                    >
                      {progress}%
                    </div>
                    <p className="text-xs text-muted-foreground">Complete</p>
                  </div>
                </div>

                {/* Enhanced Progress Bar */}
                <div className="relative">
                  <div className="w-full bg-violet-100 rounded-full h-3 overflow-hidden shadow-inner">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all duration-700 ease-out relative overflow-hidden',
                        'bg-gradient-to-r from-violet-500 via-violet-600 to-cyan-500',
                        'shadow-lg'
                      )}
                      style={{
                        width: `${progress}%`,
                        backgroundSize: '200% 100%',
                        animation: 'gradient-shift 2s ease-in-out infinite',
                      }}
                    >
                      <div
                        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                        style={{ animation: 'shimmer 1.5s ease-in-out infinite' }}
                      />
                    </div>
                  </div>
                  {/* Progress milestones */}
                  <div className="flex justify-between mt-2 px-1">
                    {[
                      { label: 'Started', threshold: 25 },
                      { label: 'Analyzing', threshold: 50 },
                      { label: 'Matching', threshold: 75 },
                      { label: 'Complete', threshold: 100 },
                    ].map(({ label, threshold }) => (
                      <span
                        key={label}
                        className={cn(
                          'text-xs font-medium transition-colors duration-300',
                          progress >= threshold ? 'text-violet-600' : 'text-muted-foreground'
                        )}
                      >
                        {progress >= threshold ? '✓' : '○'} {label}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Add keyframe animations */}
        <style>{`
          @keyframes gradient-shift {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
          }
          @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
          }
        `}</style>

        {/* Error Message — only for real (non-zero-results) errors */}
        {error && !isNoResultsError && (
          <Card className="max-w-2xl mx-auto border-destructive">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-destructive">Error</h3>
                  <p className="text-sm text-muted-foreground mt-1">{error}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Skills Section */}
        {skillsFound.length > 0 && (
          <Card className="max-w-4xl mx-auto">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-violet-600" />
                Skills Detected in Your Resume
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {skillsFound.map((skill, index) => (
                  <Badge
                    key={index}
                    variant="secondary"
                    className="px-3 py-1 font-mono text-xs bg-violet-50 text-violet-700 border border-violet-100"
                  >
                    {skill}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Filter Controls */}
        {hasResults && jobs.length > 0 && (
          <Card className="max-w-4xl mx-auto">
            <CardContent className="pt-6">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Sort by:</span>
                  <div className="flex gap-2 flex-wrap">
                    <Button
                      variant={sortOrder === 'desc' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => handleSortChange('desc')}
                      className="flex items-center gap-2"
                    >
                      <ArrowDown className="h-4 w-4" />
                      Highest Match
                    </Button>
                    <Button
                      variant={sortOrder === 'asc' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => handleSortChange('asc')}
                      className="flex items-center gap-2"
                    >
                      <ArrowUp className="h-4 w-4" />
                      Lowest Match
                    </Button>
                    <Button
                      variant={sortOrder === 'recent' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => handleSortChange('recent')}
                      className="flex items-center gap-2"
                    >
                      <Clock className="h-4 w-4" />
                      Most Recent
                    </Button>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>
                    Showing {Math.min((currentPage - 1) * itemsPerPage + 1, sortedJobs.length)}–
                    {Math.min(currentPage * itemsPerPage, sortedJobs.length)} of {sortedJobs.length} results
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Debug Section - Remove in production */}
        {process.env.NODE_ENV === 'development' && (jobs.length > 0 || hasResults) && (
          <Card className="max-w-4xl mx-auto bg-muted/50">
            <CardHeader>
              <CardTitle className="text-lg">Debug Information</CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-2">
              <p><strong>Has Results:</strong> {hasResults.toString()}</p>
              <p><strong>Jobs Count:</strong> {jobs.length}</p>
              <p><strong>Skills Found:</strong> {skillsFound.length}</p>
              <p><strong>Current Step:</strong> {currentStep}</p>
              <p><strong>Progress:</strong> {progress}%</p>
              {jobs.length > 0 && (
                <details className="mt-2">
                  <summary className="cursor-pointer font-medium">Job Scores</summary>
                  <div className="mt-2 space-y-1">
                    {jobs.map((job, index) => (
                      <p key={index} className="text-xs">
                        {index + 1}. {job.company} - {job.title}: {job.match_score || job.score || 0}%
                      </p>
                    ))}
                  </div>
                </details>
              )}
            </CardContent>
          </Card>
        )}

        {/* Results Section */}
        {hasResults && (
          <div className="space-y-6" id="results-section">
            <div className="text-center">
              <h2 className="text-3xl font-bold" style={{ fontFamily: 'Sora, sans-serif' }}>
                {jobs.length > 0
                  ? `You matched ${jobs.length} internships — here are your best fits`
                  : 'No Matches Found'}
              </h2>
              <p className="text-muted-foreground mt-2">
                {jobs.length > 0
                  ? 'AI-powered career fit analysis · Sorted by compatibility score'
                  : 'Try updating your resume with more technical skills'}
              </p>
              {jobs.length > 0 && (
                <div className="flex justify-center gap-4 mt-4 flex-wrap">
                  <Badge
                    variant="secondary"
                    className="px-3 py-1 bg-violet-50 text-violet-700 border border-violet-100"
                  >
                    <Sparkles className="h-4 w-4 mr-1" />
                    Intelligent Matching
                  </Badge>
                  <Badge variant="outline" className="px-3 py-1">
                    All {jobs.length} Results
                  </Badge>
                  {fromCache && (
                    <Badge
                      variant="secondary"
                      className="px-3 py-1 bg-cyan-50 text-cyan-700 border border-cyan-100"
                    >
                      Loaded from cache
                    </Badge>
                  )}
                </div>
              )}
            </div>

            <div className="grid gap-4 max-w-4xl mx-auto">
              {jobs.length > 0 ? (
                currentPageJobs.map((job, index) => (
                  <div
                    key={`${job.company}-${job.title}-${(currentPage - 1) * itemsPerPage + index}`}
                    className="transition-all duration-300 hover:-translate-y-1"
                  >
                    <JobCard
                      job={job}
                      isNewResult={isLoading && useStreaming}
                      resumeFile={selectedFile}
                      apiBaseUrl={API_BASE_URL}
                    />
                  </div>
                ))
              ) : isNoResultsError ? (
                /* ── Helpful empty state ── */
                <div className="max-w-2xl mx-auto rounded-2xl border border-neutral-200 bg-white p-10 text-center shadow-sm">
                  <div className="h-14 w-14 rounded-2xl bg-violet-50 border border-violet-100 flex items-center justify-center mx-auto mb-5">
                    <Sparkles className="h-7 w-7 text-violet-400" />
                  </div>
                  <h3 className="text-xl font-semibold text-neutral-900 mb-2" style={{ fontFamily: 'Sora, sans-serif' }}>
                    No matches found yet
                  </h3>
                  <p className="text-neutral-500 text-sm leading-relaxed mb-5 max-w-md mx-auto">
                    We scanned our database but couldn't find a strong fit for your current resume.
                    This usually means your resume is missing technical keywords or project details.
                  </p>
                  {skillsFound.length > 0 && (
                    <div className="mb-6">
                      <p className="text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-2">
                        Skills we detected
                      </p>
                      <div className="flex flex-wrap gap-1.5 justify-center">
                        {skillsFound.map((skill, i) => (
                          <span
                            key={i}
                            className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-violet-50 text-violet-700 border border-violet-100"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <ul className="text-sm text-neutral-500 text-left max-w-xs mx-auto space-y-1.5 mb-6">
                    <li className="flex items-start gap-2">
                      <span className="text-violet-400 font-bold mt-0.5">·</span>
                      Add specific tech stacks, languages, and frameworks
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-violet-400 font-bold mt-0.5">·</span>
                      Include project names with measurable outcomes
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-violet-400 font-bold mt-0.5">·</span>
                      List coursework or certifications relevant to your field
                    </li>
                  </ul>
                  <button
                    onClick={handleTryAgain}
                    className="inline-flex items-center gap-2 rounded-full px-6 py-2.5 bg-violet-600 hover:bg-violet-700 text-white text-sm font-semibold shadow-md shadow-violet-500/20 transition-all hover:-translate-y-0.5"
                  >
                    <RefreshCcw className="h-4 w-4" />
                    Try Again with a New Resume
                  </button>
                </div>
              ) : null}
            </div>

            {/* Pagination Controls */}
            {jobs.length > itemsPerPage && (
              <Card className="max-w-4xl mx-auto">
                <CardContent className="pt-6">
                  <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={currentPage === 1}
                        className="flex items-center gap-2"
                      >
                        <ChevronLeft className="h-4 w-4" />
                        Previous
                      </Button>

                      <div className="flex items-center gap-1">
                        {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                          let pageNum: number;
                          if (totalPages <= 5) {
                            pageNum = i + 1;
                          } else if (currentPage <= 3) {
                            pageNum = i + 1;
                          } else if (currentPage >= totalPages - 2) {
                            pageNum = totalPages - 4 + i;
                          } else {
                            pageNum = currentPage - 2 + i;
                          }

                          return (
                            <Button
                              key={pageNum}
                              variant={currentPage === pageNum ? 'default' : 'outline'}
                              size="sm"
                              onClick={() => handlePageChange(pageNum)}
                              className="w-10 h-10"
                            >
                              {pageNum}
                            </Button>
                          );
                        })}
                      </div>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={currentPage === totalPages}
                        className="flex items-center gap-2"
                      >
                        Next
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>

                    <div className="text-sm text-muted-foreground">
                      Page {currentPage} of {totalPages}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default FindPage;
