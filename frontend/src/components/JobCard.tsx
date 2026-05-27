import React, { useState } from 'react';
import { Job } from '../types';
import { ExternalLink, ChevronDown, ChevronUp, AlertTriangle, Target, CheckCircle2 } from 'lucide-react';

interface JobCardProps {
  job: Job;
  isNewResult?: boolean;
  resumeFile?: File | null;
  apiBaseUrl?: string;
  authToken?: string | null;
}

const JobCard: React.FC<JobCardProps> = ({ job, isNewResult = false, resumeFile, apiBaseUrl = '', authToken }) => {
  const [showReasoning, setShowReasoning] = useState(false);
  const [isTailoring, setIsTailoring] = useState(false);
  const [tailorError, setTailorError] = useState('');

  const handleTailorResume = async () => {
    if (!resumeFile) return;
    setIsTailoring(true);
    setTailorError('');
    try {
      const formData = new FormData();
      formData.append('resume', resumeFile);
      formData.append('job_title', job.title || '');
      formData.append('company', job.company || '');
      formData.append('job_description', job.description || '');

      const response = await fetch(`${apiBaseUrl}/api/tailor-resume`, {
        method: 'POST',
        body: formData,
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || `Server error ${response.status}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `resume_tailored_${job.company}_${job.title}.pdf`.replace(/[^\w\-_.]/g, '_');
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setTailorError(err.message || 'Failed to tailor resume. Please try again.');
    } finally {
      setIsTailoring(false);
    }
  };

  const score = job.match_score || job.score || 0;
  const hasReasoning = job.ai_reasoning && job.ai_reasoning.reasoning;

  const getTimeAgo = (dateString?: string): string => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    const weeks = Math.floor(diffDays / 7);
    if (diffDays < 30) return `${weeks}w ago`;
    const months = Math.floor(diffDays / 30);
    return `${months}mo ago`;
  };

  const isNewJob = (dateString?: string): boolean => {
    if (!dateString) return false;
    return (new Date().getTime() - new Date(dateString).getTime()) / 3600000 <= 48;
  };

  const timeAgo = getTimeAgo(job.first_seen);
  const showNewIndicator = isNewJob(job.first_seen);

  const CUE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
    '🎯': Target,
    '✅': CheckCircle2,
    '⚠️': AlertTriangle,
    '⚠': AlertTriangle,
  };

  const formatMatchDescription = (desc: string) => {
    if (!desc) return [];
    return desc
      .split('\n')
      .map((line, index) => {
        const trimmed = line.trim();
        if (!trimmed) return null;

        // Detect leading status emoji and map to Lucide icon
        const cueKey = Object.keys(CUE_ICONS).find(k => trimmed.startsWith(k));
        const Icon = cueKey ? CUE_ICONS[cueKey] : null;
        const text = cueKey ? trimmed.slice(cueKey.length).trimStart() : trimmed;

        // Render **bold** spans as JSX — no dangerouslySetInnerHTML
        const parts = text.split(/(\*\*.*?\*\*)/g);
        const content = parts.map((part, i) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>;
          }
          return part;
        });

        return (
          <p
            key={index}
            className={`text-sm text-text-secondary flex items-start gap-1.5${trimmed.startsWith('•') ? ' ml-2' : ''}`}
          >
            {Icon && <Icon className="h-3.5 w-3.5 mt-0.5 shrink-0 text-ia" />}
            <span>{content}</span>
          </p>
        );
      })
      .filter(Boolean);
  };

  const scoreColor = score >= 90 ? 'text-emerald-400' : score >= 80 ? 'text-ia' : 'text-text-secondary';
  const barColor = score >= 90 ? 'bg-emerald-400' : score >= 80 ? 'bg-ia' : 'bg-slate-500';

  return (
    <div className="bg-surface border border-lp-border rounded-lg p-5">
      {/* Header row */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-text-primary text-base font-semibold leading-snug">{job.title}</span>
            {showNewIndicator && (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse flex-shrink-0" />
            )}
          </div>
          <div className="text-text-secondary text-sm">{job.company}</div>
          <div className="flex items-center gap-2 mt-1 text-text-tertiary text-xs">
            {job.location && <span>{job.location}</span>}
            {timeAgo && <span>· {timeAgo}</span>}
          </div>
        </div>

        {/* Score */}
        <div className="shrink-0 text-right">
          <div className={`font-serif italic text-2xl leading-none ${scoreColor}`}>{score}%</div>
          <div className="text-text-tertiary text-[10px] mt-0.5">match</div>
          <div className="w-16 h-0.5 bg-lp-border rounded-full overflow-hidden mt-1.5 ml-auto">
            <div className={`h-full rounded-full ${barColor}`} style={{ width: `${score}%` }} />
          </div>
        </div>
      </div>

      {/* Required skills */}
      {job.required_skills && job.required_skills.length > 0 && (
        <div className="mt-3 pt-3 border-t border-lp-border">
          <div className="text-text-tertiary text-[10px] uppercase tracking-wider mb-1.5">Required skills</div>
          <div className="flex flex-wrap gap-1">
            {job.required_skills.slice(0, 8).map((skill, i) => (
              <span key={i} className="text-[10px] px-1.5 py-0.5 bg-ia-subtle text-ia-pill rounded font-mono">
                {skill}
              </span>
            ))}
            {job.required_skills.length > 8 && (
              <span className="text-[10px] px-1.5 py-0.5 bg-surface text-text-tertiary rounded font-mono border border-lp-border">
                +{job.required_skills.length - 8}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Why it fits */}
      {job.match_description && (
        <div className="mt-3 pt-3 border-t border-lp-border">
          <div className="text-text-tertiary text-[10px] uppercase tracking-wider mb-1.5">Why it fits</div>
          <div className="space-y-1">{formatMatchDescription(job.match_description)}</div>
        </div>
      )}

      {/* Reasoning (Think Deeper) */}
      {hasReasoning && (
        <div className="mt-3 pt-3 border-t border-lp-border">
          <button
            type="button"
            onClick={() => setShowReasoning(!showReasoning)}
            aria-expanded={showReasoning}
            className="flex items-center gap-1.5 text-text-tertiary text-[10px] uppercase tracking-wider hover:text-text-secondary transition-colors w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ia focus-visible:ring-offset-2 focus-visible:ring-offset-bg rounded"
          >
            <span>Reasoning</span>
            {showReasoning ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>

          {showReasoning && job.ai_reasoning && (
            <div className="mt-3 space-y-3">
              {(job.ai_reasoning.resume_complexity || job.ai_reasoning.experience_match) && (
                <div className="flex items-center gap-2 flex-wrap">
                  {job.ai_reasoning.resume_complexity && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-ia-subtle text-ia-pill rounded font-mono">
                      {job.ai_reasoning.resume_complexity}
                      {job.ai_reasoning.complexity_score !== undefined && ` (${job.ai_reasoning.complexity_score}/100)`}
                    </span>
                  )}
                  {job.ai_reasoning.experience_match && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-ia-subtle text-ia-pill rounded font-mono">
                      {job.ai_reasoning.experience_match} fit
                    </span>
                  )}
                </div>
              )}

              <p className="text-sm text-text-secondary leading-relaxed">{job.ai_reasoning.reasoning}</p>

              {job.ai_reasoning.skill_matches && job.ai_reasoning.skill_matches.length > 0 && (
                <div>
                  <div className="text-text-tertiary text-[10px] uppercase tracking-wider mb-1">Your matching skills</div>
                  <div className="flex flex-wrap gap-1">
                    {job.ai_reasoning.skill_matches.map((s, i) => (
                      <span key={i} className="text-[10px] px-1.5 py-0.5 bg-emerald-950/50 text-emerald-400 rounded font-mono">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {job.ai_reasoning.skill_gaps && job.ai_reasoning.skill_gaps.length > 0 && (
                <div>
                  <div className="text-text-tertiary text-[10px] uppercase tracking-wider mb-1">Skills to develop</div>
                  <div className="flex flex-wrap gap-1">
                    {job.ai_reasoning.skill_gaps.slice(0, 5).map((s, i) => (
                      <span key={i} className="text-[10px] px-1.5 py-0.5 bg-surface text-text-tertiary rounded font-mono border border-lp-border">
                        {s}
                      </span>
                    ))}
                    {job.ai_reasoning.skill_gaps.length > 5 && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-surface text-text-tertiary rounded font-mono border border-lp-border">
                        +{job.ai_reasoning.skill_gaps.length - 5}
                      </span>
                    )}
                  </div>
                </div>
              )}

              {job.ai_reasoning.red_flags && job.ai_reasoning.red_flags.length > 0 && (
                <div>
                  <div className="text-text-tertiary text-[10px] uppercase tracking-wider mb-1 flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    Considerations
                  </div>
                  <ul className="space-y-1">
                    {job.ai_reasoning.red_flags.map((flag, i) => (
                      <li key={i} className="text-sm text-red-300 flex items-start gap-2">
                        <span className="text-red-400 mt-1 shrink-0">·</span>
                        {flag}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      {((job.apply_link || job.url) || resumeFile) && (
        <div className="mt-4 pt-4 border-t border-lp-border flex flex-wrap gap-3 items-center">
          {(job.apply_link || job.url) && (
            <button
              onClick={() => window.open(job.apply_link || job.url, '_blank', 'noopener,noreferrer')}
              className="inline-flex items-center gap-1.5 bg-ia text-bg px-3 py-1.5 rounded-md text-xs font-semibold hover:bg-ia-hover transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ia focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Apply Now
            </button>
          )}
          {resumeFile && (
            <button
              onClick={handleTailorResume}
              disabled={isTailoring}
              className="text-ia hover:text-ia-hover text-xs font-medium transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ia focus-visible:ring-offset-2 focus-visible:ring-offset-bg rounded"
            >
              {isTailoring ? 'Tailoring...' : 'Tailor Resume for This Job'}
            </button>
          )}
          {tailorError && <p className="text-xs text-red-400 w-full">{tailorError}</p>}
        </div>
      )}
    </div>
  );
};

export default JobCard;
