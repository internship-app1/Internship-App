import React, { useMemo, useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface CodeSnippetProps {
  title: string;
  subtitle?: string;
  code: string;
  copyText?: string;
  footer?: React.ReactNode;
  className?: string;
}

const CodeSnippet: React.FC<CodeSnippetProps> = ({
  title,
  subtitle,
  code,
  copyText,
  footer,
  className,
}) => {
  const [copied, setCopied] = useState(false);
  const lines = useMemo(() => code.replace(/\s+$/, '').split('\n'), [code]);

  const copy = async () => {
    await navigator.clipboard.writeText(copyText ?? code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  };

  return (
    <div className={`code-snippet ${className ?? ''}`}>
      <div className="code-snippet__chrome flex items-center justify-between gap-4 border-b px-4 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex shrink-0 items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-white/25" />
            <span className="h-2.5 w-2.5 rounded-full bg-white/18" />
            <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
          </div>
          <div className="min-w-0">
            <div className="truncate font-sans text-[12px] font-medium text-[var(--code-snippet-text)]">
              {title}
            </div>
            {subtitle && (
              <div className="truncate font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--code-snippet-muted)]">
                {subtitle}
              </div>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={copy}
          className="inline-flex shrink-0 items-center gap-2 rounded-md border border-white/10 bg-white/5 px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--code-snippet-muted)] transition-colors hover:border-white/20 hover:text-[var(--code-snippet-text)]"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>

      <div className="code-snippet__body overflow-x-auto">
        <div className="min-w-max py-3 font-mono text-[12.5px] leading-6 text-[var(--code-snippet-text)]">
          {lines.map((line, index) => (
            <div key={index} className="code-snippet__row grid grid-cols-[3.25rem_minmax(0,1fr)] gap-4 px-4">
              <span className="select-none text-right text-[11px] text-[var(--code-snippet-muted)] opacity-70">
                {index + 1}
              </span>
              <span className="whitespace-pre">{line || ' '}</span>
            </div>
          ))}
        </div>
      </div>

      {footer && (
        <div className="border-t border-white/8 px-4 py-3 font-sans text-[12px] leading-6 text-[var(--code-snippet-muted)]">
          {footer}
        </div>
      )}
    </div>
  );
};

export default CodeSnippet;
