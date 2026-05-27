import React from 'react';
import { Brain } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ThinkDeeperToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
}

export const ThinkDeeperToggle: React.FC<ThinkDeeperToggleProps> = ({ checked, onChange }) => {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cn(
        'w-full text-left border p-3.5 transition-colors cursor-pointer',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ia focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
        checked
          ? 'border-ia bg-ia-subtle'
          : 'border-lp-border bg-surface hover:border-ia/50'
      )}
    >
      <div className="flex items-center gap-3">
        <div className={cn(
          'flex-shrink-0 h-8 w-8 flex items-center justify-center transition-colors',
          checked ? 'bg-ia text-bg' : 'bg-lp-border/20 text-text-tertiary'
        )}>
          <Brain className="h-4 w-4" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className={cn(
              'text-sm font-semibold transition-colors',
              checked ? 'text-text-primary' : 'text-text-secondary'
            )}>
              Think Deeper
            </span>
            <div className={cn(
              'relative flex-shrink-0 h-5 w-9 rounded-full transition-colors',
              checked ? 'bg-ia' : 'bg-lp-border'
            )}>
              <span className={cn(
                'absolute top-0.5 h-4 w-4 rounded-full bg-bg shadow-sm transition-transform duration-200',
                checked ? 'translate-x-4' : 'translate-x-0.5'
              )} />
            </div>
          </div>
          <p className="text-xs mt-0.5 text-text-tertiary">
            Skill gap analysis, red flags &amp; career fit.{' '}
            <span className="font-medium">~30s longer.</span>
          </p>
        </div>
      </div>

      {checked && (
        <div className="flex items-center gap-4 pt-3 mt-2 border-t border-lp-border">
          {['Skill Gaps', 'Red Flags', 'Career Fit'].map((label) => (
            <span key={label} className="flex items-center gap-1 text-xs font-mono text-ia">
              <span className="h-1.5 w-1.5 rounded-full bg-ia flex-shrink-0" />
              {label}
            </span>
          ))}
        </div>
      )}
    </button>
  );
};
