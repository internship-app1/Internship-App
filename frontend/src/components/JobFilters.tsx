import React, { useState } from 'react';
import { SlidersHorizontal, ChevronDown, X } from 'lucide-react';
import { cn } from '../lib/utils';

export type CitizenshipPref = 'any' | 'citizen' | 'non_citizen';

export interface JobFilterState {
  locations: string;        // comma-separated free text
  positions: string[];      // category ids (see POSITION_OPTIONS)
  companySizes: string[];   // 'startup' | 'midsize' | 'large'
  citizenship: CitizenshipPref;
  avoidCompanies: string;   // comma-separated free text
}

export const EMPTY_FILTERS: JobFilterState = {
  locations: '',
  positions: [],
  companySizes: [],
  citizenship: 'any',
  avoidCompanies: '',
};

// Position category ids MUST match POSITION_KEYWORDS keys in matching/job_filters.py
const POSITION_OPTIONS: { id: string; label: string }[] = [
  { id: 'software_engineer', label: 'Software Engineer' },
  { id: 'frontend', label: 'Frontend' },
  { id: 'backend', label: 'Backend' },
  { id: 'fullstack', label: 'Full Stack' },
  { id: 'data_science', label: 'Data Science / Analytics' },
  { id: 'data_engineering', label: 'Data Engineering' },
  { id: 'machine_learning', label: 'ML / AI' },
  { id: 'mobile', label: 'Mobile' },
  { id: 'devops', label: 'DevOps / SRE' },
  { id: 'security', label: 'Security' },
  { id: 'qa', label: 'QA / Test' },
  { id: 'hardware', label: 'Hardware / Embedded' },
];

const COMPANY_SIZE_OPTIONS: { id: string; label: string }[] = [
  { id: 'startup', label: 'Startup' },
  { id: 'midsize', label: 'Mid-size' },
  { id: 'large', label: 'Large / Enterprise' },
];

const CITIZENSHIP_OPTIONS: { id: CitizenshipPref; label: string }[] = [
  { id: 'any', label: "Doesn't matter" },
  { id: 'citizen', label: "I'm a U.S. citizen" },
  { id: 'non_citizen', label: 'Not a citizen — need sponsorship' },
];

export function isFilterActive(f: JobFilterState): boolean {
  return Boolean(
    f.locations.trim() ||
    f.positions.length ||
    f.companySizes.length ||
    f.avoidCompanies.trim() ||
    f.citizenship !== 'any'
  );
}

/** Stable signature used to key the result cache per filter combination. */
export function filterSignature(f: JobFilterState): string {
  const norm = (s: string) =>
    s.split(',').map(p => p.trim().toLowerCase()).filter(Boolean).sort().join('|');
  return [
    norm(f.locations),
    [...f.positions].sort().join('|'),
    [...f.companySizes].sort().join('|'),
    f.citizenship,
    norm(f.avoidCompanies),
  ].join('::');
}

interface JobFiltersProps {
  value: JobFilterState;
  onChange: (next: JobFilterState) => void;
  disabled?: boolean;
}

const focusRing =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ia focus-visible:ring-offset-2 focus-visible:ring-offset-bg';

const JobFilters: React.FC<JobFiltersProps> = ({ value, onChange, disabled }) => {
  const [open, setOpen] = useState(false);
  const active = isFilterActive(value);

  const activeCount =
    (value.locations.trim() ? 1 : 0) +
    value.positions.length +
    value.companySizes.length +
    (value.avoidCompanies.trim() ? 1 : 0) +
    (value.citizenship !== 'any' ? 1 : 0);

  const toggleInArray = (arr: string[], id: string): string[] =>
    arr.includes(id) ? arr.filter(x => x !== id) : [...arr, id];

  const chip = (selected: boolean, label: string, onClick: () => void) => (
    <button
      key={label}
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'font-mono text-[11px] px-2.5 py-1 border transition-colors disabled:opacity-40',
        focusRing,
        selected
          ? 'border-ia bg-ia-subtle text-text-primary'
          : 'border-lp-border text-text-secondary hover:border-ia/50'
      )}
    >
      {label}
    </button>
  );

  const sectionLabel = (text: string) => (
    <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-2">
      {text}
    </div>
  );

  return (
    <div className="border border-lp-border bg-surface">
      {/* Header / toggle */}
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className={cn('w-full flex items-center justify-between gap-3 p-3.5 text-left', focusRing)}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className={cn(
            'flex-shrink-0 h-8 w-8 flex items-center justify-center transition-colors',
            active ? 'bg-ia text-bg' : 'bg-lp-border/20 text-text-tertiary'
          )}>
            <SlidersHorizontal className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <span className={cn('text-sm font-semibold', active ? 'text-text-primary' : 'text-text-secondary')}>
              Filters
            </span>
            <p className="text-xs mt-0.5 text-text-tertiary truncate">
              {active ? `${activeCount} filter${activeCount !== 1 ? 's' : ''} applied` : 'Narrow results by location, role, company & more'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {active && (
            <span
              role="button"
              tabIndex={0}
              onClick={(e) => { e.stopPropagation(); onChange(EMPTY_FILTERS); }}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); onChange(EMPTY_FILTERS); } }}
              className="inline-flex items-center gap-1 font-mono text-[10px] text-text-tertiary hover:text-text-primary transition-colors"
            >
              <X className="h-3 w-3" /> Clear
            </span>
          )}
          <ChevronDown className={cn('h-4 w-4 text-text-tertiary transition-transform', open && 'rotate-180')} />
        </div>
      </button>

      {/* Body */}
      {open && (
        <div className="border-t border-lp-border p-4 space-y-5">
          {/* Location */}
          <div>
            {sectionLabel('Location')}
            <input
              type="text"
              value={value.locations}
              disabled={disabled}
              onChange={(e) => onChange({ ...value, locations: e.target.value })}
              placeholder="e.g. New York, San Francisco, Remote"
              className={cn(
                'w-full bg-bg border border-lp-border px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary',
                focusRing
              )}
            />
            <p className="font-mono text-[10px] text-text-tertiary mt-1">Comma-separated. Matches city, state, or "Remote".</p>
          </div>

          {/* Position */}
          <div>
            {sectionLabel('Position')}
            <div className="flex flex-wrap gap-1.5">
              {POSITION_OPTIONS.map(opt =>
                chip(value.positions.includes(opt.id), opt.label, () =>
                  onChange({ ...value, positions: toggleInArray(value.positions, opt.id) })
                )
              )}
            </div>
          </div>

          {/* Company size */}
          <div>
            {sectionLabel('Company size')}
            <div className="flex flex-wrap gap-1.5">
              {COMPANY_SIZE_OPTIONS.map(opt =>
                chip(value.companySizes.includes(opt.id), opt.label, () =>
                  onChange({ ...value, companySizes: toggleInArray(value.companySizes, opt.id) })
                )
              )}
            </div>
            <p className="font-mono text-[10px] text-text-tertiary mt-1">Best-effort — based on a list of well-known large employers.</p>
          </div>

          {/* Citizenship */}
          <div>
            {sectionLabel('U.S. citizenship')}
            <div className="flex flex-wrap gap-1.5">
              {CITIZENSHIP_OPTIONS.map(opt =>
                chip(value.citizenship === opt.id, opt.label, () =>
                  onChange({ ...value, citizenship: opt.id })
                )
              )}
            </div>
            {value.citizenship === 'non_citizen' && (
              <p className="font-mono text-[10px] text-text-tertiary mt-1">Hides roles requiring U.S. citizenship or that don't offer sponsorship.</p>
            )}
          </div>

          {/* Companies to avoid */}
          <div>
            {sectionLabel('Companies to avoid')}
            <input
              type="text"
              value={value.avoidCompanies}
              disabled={disabled}
              onChange={(e) => onChange({ ...value, avoidCompanies: e.target.value })}
              placeholder="e.g. Amazon, Meta"
              className={cn(
                'w-full bg-bg border border-lp-border px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary',
                focusRing
              )}
            />
            <p className="font-mono text-[10px] text-text-tertiary mt-1">Comma-separated. These companies are excluded from results.</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default JobFilters;
