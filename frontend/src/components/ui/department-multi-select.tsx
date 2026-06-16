import React from 'react';
import { Layers } from 'lucide-react';
import { cn } from '../../lib/utils';

// Mirrors job_categories.CATEGORIES on the backend (id + label). 'other' is the
// catch-all and intentionally selectable so users can include unclassified roles.
export const DEPARTMENT_CATEGORIES: { id: string; label: string }[] = [
  { id: 'software', label: 'Software Engineering' },
  { id: 'data_ml', label: 'Data / ML / AI' },
  { id: 'hardware', label: 'Hardware / Embedded' },
  { id: 'security', label: 'Security' },
  { id: 'product', label: 'Product' },
  { id: 'design', label: 'Design / UX' },
  { id: 'business', label: 'Business & Other' },
  { id: 'other', label: 'Other / Unclassified' },
];

interface DepartmentMultiSelectProps {
  selected: string[];
  onChange: (selected: string[]) => void;
}

export const DepartmentMultiSelect: React.FC<DepartmentMultiSelectProps> = ({ selected, onChange }) => {
  const toggle = (id: string) => {
    onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);
  };

  const active = selected.length > 0;

  return (
    <div
      className={cn(
        'w-full border p-3.5 transition-colors',
        active ? 'border-ia bg-ia-subtle' : 'border-lp-border bg-surface'
      )}
    >
      <div className="flex items-center gap-3">
        <div
          className={cn(
            'flex-shrink-0 h-8 w-8 flex items-center justify-center transition-colors',
            active ? 'bg-ia text-bg' : 'bg-lp-border/20 text-text-tertiary'
          )}
        >
          <Layers className="h-4 w-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span
              className={cn(
                'text-sm font-semibold transition-colors',
                active ? 'text-text-primary' : 'text-text-secondary'
              )}
            >
              Departments
            </span>
            {active && (
              <button
                type="button"
                onClick={() => onChange([])}
                className="text-xs font-medium text-text-tertiary hover:text-text-primary transition-colors"
              >
                Clear
              </button>
            )}
          </div>
          <p className="text-xs mt-0.5 text-text-tertiary">
            {active
              ? `Showing ${selected.length} selected ${selected.length === 1 ? 'category' : 'categories'}.`
              : 'All departments. Select to narrow to specific fields.'}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 pt-3 mt-2 border-t border-lp-border">
        {DEPARTMENT_CATEGORIES.map(({ id, label }) => {
          const on = selected.includes(id);
          return (
            <button
              key={id}
              type="button"
              role="checkbox"
              aria-checked={on}
              onClick={() => toggle(id)}
              className={cn(
                'text-xs font-medium px-2.5 py-1 border transition-colors cursor-pointer',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ia focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
                on
                  ? 'border-ia bg-ia text-bg'
                  : 'border-lp-border bg-surface text-text-secondary hover:border-ia/50'
              )}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
};
