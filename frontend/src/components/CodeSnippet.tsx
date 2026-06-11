import React, { useMemo, useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { Highlight, codeThemeDark, codeThemeLight, normalizeLang } from '../lib/highlight';
import { useResolvedTheme } from './theme-provider';

interface CodeSnippetProps {
  title: string;
  subtitle?: string;
  code: string;
  language?: string;
  wrap?: boolean;
  copyText?: string;
  footer?: React.ReactNode;
  className?: string;
}

const LANG_BADGES: Record<string, string> = {
  json: 'JSON',
  toml: 'TOML',
  bash: 'BASH',
  python: 'PY',
  javascript: 'JS',
  typescript: 'TS',
};

const CodeSnippet: React.FC<CodeSnippetProps> = ({
  title,
  subtitle,
  code,
  language,
  wrap = false,
  copyText,
  footer,
  className,
}) => {
  const [copied, setCopied] = useState(false);
  const resolvedTheme = useResolvedTheme();
  const trimmed = useMemo(() => code.replace(/\s+$/, ''), [code]);
  const lang = normalizeLang(language);
  const badge = LANG_BADGES[lang];
  const prismTheme = resolvedTheme === 'dark' ? codeThemeDark : codeThemeLight;

  const copy = async () => {
    await navigator.clipboard.writeText(copyText ?? code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  };

  return (
    <div className={`code-snippet ${className ?? ''}`}>
      <div className="code-snippet__chrome flex items-center justify-between gap-4 border-b px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-3">
          {badge && (
            <span className="shrink-0 rounded border border-[var(--code-snippet-border)] px-1.5 py-0.5 font-mono text-[10px] font-medium tracking-wider text-[var(--code-snippet-muted)]">
              {badge}
            </span>
          )}
          <div className="min-w-0">
            <div className="truncate font-mono text-[12px] font-medium text-[var(--code-snippet-text)]">
              {title}
            </div>
            {subtitle && (
              <div className="truncate font-sans text-[11px] text-[var(--code-snippet-muted)]">
                {subtitle}
              </div>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={copy}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-[var(--code-snippet-border)] px-2.5 py-1.5 font-sans text-[11px] font-medium text-[var(--code-snippet-muted)] transition-colors hover:text-[var(--code-snippet-text)]"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>

      <div className="code-snippet__body overflow-x-auto">
        <Highlight code={trimmed} language={lang} theme={prismTheme}>
          {({ tokens, getLineProps, getTokenProps }) => (
            <div className={`py-3 font-mono text-[13px] leading-6 text-[var(--code-snippet-text)] ${wrap ? '' : 'min-w-max'}`}>
              {tokens.map((line, index) => (
                <div
                  {...getLineProps({ line })}
                  key={index}
                  className="code-snippet__row grid grid-cols-[3.25rem_minmax(0,1fr)] gap-4 px-4"
                >
                  <span className="select-none text-right text-[11px] leading-6 text-[var(--code-snippet-muted)] opacity-70">
                    {index + 1}
                  </span>
                  <span className={wrap ? 'whitespace-pre-wrap break-words' : 'whitespace-pre'}>
                    {line.map((token, tokenIndex) => (
                      <span {...getTokenProps({ token })} key={tokenIndex} />
                    ))}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Highlight>
      </div>

      {footer && (
        <div className="border-t border-[var(--code-snippet-border)] px-4 py-3 font-sans text-[12px] leading-6 text-[var(--code-snippet-muted)]">
          {footer}
        </div>
      )}
    </div>
  );
};

export default CodeSnippet;
