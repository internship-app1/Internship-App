import { Highlight, Prism, PrismTheme } from 'prism-react-renderer';

// prism-react-renderer ships json/bash/python/javascript but not TOML.
// Registering the grammar requires the global Prism hook, done once here.
(globalThis as any).Prism = Prism;
// eslint-disable-next-line @typescript-eslint/no-var-requires
require('prismjs/components/prism-toml');

export { Highlight };

const LANG_ALIASES: Record<string, string> = {
  js: 'javascript',
  ts: 'typescript',
  shell: 'bash',
  sh: 'bash',
  curl: 'bash',
  py: 'python',
};

export function normalizeLang(lang?: string): string {
  if (!lang) return 'plain';
  const lower = lang.toLowerCase();
  return LANG_ALIASES[lower] ?? lower;
}

/* Backgrounds stay transparent so the CodeSnippet panel color wins. */

export const codeThemeDark: PrismTheme = {
  plain: { color: '#dbe7f5', backgroundColor: 'transparent' },
  styles: [
    { types: ['comment', 'prolog', 'doctype', 'cdata'], style: { color: '#64748b', fontStyle: 'italic' } },
    { types: ['punctuation'], style: { color: '#8a98ab' } },
    { types: ['property', 'tag', 'constant', 'symbol', 'deleted'], style: { color: '#7dd3fc' } },
    { types: ['boolean', 'number'], style: { color: '#fda4af' } },
    { types: ['selector', 'attr-name', 'string', 'char', 'builtin', 'inserted'], style: { color: '#86efac' } },
    { types: ['operator', 'entity', 'url'], style: { color: '#93c5fd' } },
    { types: ['atrule', 'attr-value', 'keyword'], style: { color: '#c4b5fd' } },
    { types: ['function', 'class-name'], style: { color: '#fcd34d' } },
    { types: ['regex', 'important', 'variable'], style: { color: '#fdba74' } },
    { types: ['table'], style: { color: '#7dd3fc' } },
  ],
};

export const codeThemeLight: PrismTheme = {
  plain: { color: '#24292f', backgroundColor: 'transparent' },
  styles: [
    { types: ['comment', 'prolog', 'doctype', 'cdata'], style: { color: '#6e7781', fontStyle: 'italic' } },
    { types: ['punctuation'], style: { color: '#57606a' } },
    { types: ['property', 'tag', 'constant', 'symbol', 'deleted'], style: { color: '#0550ae' } },
    { types: ['boolean', 'number'], style: { color: '#cf222e' } },
    { types: ['selector', 'attr-name', 'string', 'char', 'builtin', 'inserted'], style: { color: '#0a7d4f' } },
    { types: ['operator', 'entity', 'url'], style: { color: '#0550ae' } },
    { types: ['atrule', 'attr-value', 'keyword'], style: { color: '#8250df' } },
    { types: ['function', 'class-name'], style: { color: '#953800' } },
    { types: ['regex', 'important', 'variable'], style: { color: '#bc4c00' } },
    { types: ['table'], style: { color: '#0550ae' } },
  ],
};
