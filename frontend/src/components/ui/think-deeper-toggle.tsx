import React from 'react';
import { Brain } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ThinkDeeperToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
}

export const ThinkDeeperToggle: React.FC<ThinkDeeperToggleProps> = ({
  checked,
  onChange,
}) => {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cn(
        'w-full text-left rounded-2xl border-2 p-4 transition-all duration-300 cursor-pointer',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2',
        !checked && [
          'border-border',
          'bg-card',
          'hover:border-violet-300 hover:bg-violet-50/30',
          'dark:hover:border-violet-700 dark:hover:bg-violet-950/30',
        ],
        checked && [
          'border-violet-500/70',
          'bg-gradient-to-br from-violet-50 to-cyan-50/40',
          'shadow-lg shadow-violet-500/15',
          'dark:from-violet-950/60 dark:to-cyan-950/30',
          'dark:border-violet-500/50',
          'dark:shadow-violet-500/20',
        ]
      )}
    >
      <div className="flex items-start gap-3">
        {/* Icon — glows when ON */}
        <div
          className={cn(
            'mt-0.5 flex-shrink-0 h-9 w-9 rounded-xl flex items-center justify-center transition-all duration-300',
            !checked && 'bg-muted text-muted-foreground',
            checked && [
              'bg-gradient-to-br from-violet-500 to-cyan-500',
              'text-white',
              'shadow-md shadow-violet-500/30',
            ]
          )}
        >
          <Brain className="h-[18px] w-[18px]" />
        </div>

        {/* Text */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span
              className={cn(
                'text-sm font-semibold transition-colors duration-300',
                !checked && 'text-foreground',
                checked && 'text-violet-700 dark:text-violet-300'
              )}
              style={{ fontFamily: 'Sora, sans-serif' }}
            >
              Think Deeper
            </span>

            {/* Toggle track */}
            <div
              className={cn(
                'relative flex-shrink-0 h-5 w-9 rounded-full transition-all duration-300',
                !checked && 'bg-muted',
                checked && 'bg-gradient-to-r from-violet-500 to-cyan-500'
              )}
            >
              <span
                className={cn(
                  'absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-300',
                  !checked ? 'translate-x-0.5' : 'translate-x-4'
                )}
              />
            </div>
          </div>

          <p
            className={cn(
              'text-xs mt-1 leading-relaxed transition-colors duration-300',
              !checked && 'text-muted-foreground',
              checked && 'text-violet-600/80 dark:text-violet-400/80'
            )}
          >
            Skill gap analysis, red flags &amp; career fit.{' '}
            <span className="font-medium">~30s longer.</span>
          </p>
        </div>
      </div>

      {/* Expanded detail — only when ON */}
      <div
        className={cn(
          'overflow-hidden transition-all duration-300',
          !checked ? 'max-h-0 opacity-0 mt-0' : 'max-h-20 opacity-100 mt-3'
        )}
      >
        <div className="flex items-center gap-4 pt-3 border-t border-violet-200/60 dark:border-violet-700/40">
          {['Skill Gaps', 'Red Flags', 'Career Fit'].map((label) => (
            <span
              key={label}
              className="flex items-center gap-1 text-xs font-mono font-medium text-violet-600 dark:text-violet-400"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-violet-500 to-cyan-500 flex-shrink-0" />
              {label}
            </span>
          ))}
        </div>
      </div>
    </button>
  );
};
