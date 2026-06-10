import React, { useCallback, useEffect, useState } from 'react';
import { useAuth, SignInButton } from '@clerk/react';
import Header from '../components/Header';
import CodeSnippet from '../components/CodeSnippet';
import McpSetupDropdown from '../components/McpSetupDropdown';
import { API_BASE_URL } from '../lib/api';
import { useUsage } from '../hooks/useUsage';
import {
  getMcpClient,
  getMcpMode,
  getMcpSetup,
  MCP_CLIENTS,
  MCP_MODES,
  McpClientId,
  McpSetupMode,
} from '../data/mcpSetup';

interface ApiKeyMeta {
  id: number;
  key_prefix: string;
  name: string | null;
  created_at: string | null;
  last_used: string | null;
  revoked: boolean;
}

function currentOrigin(): string {
  return typeof window === 'undefined' ? 'https://internshipmatcher.com' : window.location.origin;
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  const normalized = iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z';
  return new Date(normalized).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

const CLIENT_DROPDOWN_ITEMS = MCP_CLIENTS.map((client) => ({
  ...client,
  group: 'AI agent CLI',
  icon: client.label.split(' ').map((word) => word[0]).join('').slice(0, 2),
}));

const MODE_DROPDOWN_ITEMS = MCP_MODES.map((mode) => ({
  ...mode,
  group: 'Setup path',
  icon: mode.shortLabel.slice(0, 2),
}));

const DeveloperPage: React.FC = () => {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const { data: usage } = useUsage();
  const [keys, setKeys] = useState<ApiKeyMeta[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [freshKey, setFreshKey] = useState('');
  const [copied, setCopied] = useState(false);
  const [client, setClient] = useState<McpClientId>('codex');
  const [mode, setMode] = useState<McpSetupMode>('uvx');

  const fetchKeys = useCallback(async () => {
    if (!isSignedIn) return;
    setLoading(true);
    setError('');
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE_URL}/api/developer/keys`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const json = await res.json();
      setKeys(json.keys);
    } catch (e: any) {
      setError(e.message ?? 'Failed to load keys.');
    } finally {
      setLoading(false);
    }
  }, [isSignedIn, getToken]);

  useEffect(() => { fetchKeys(); }, [fetchKeys]);

  const createKey = async () => {
    setCreating(true);
    setError('');
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE_URL}/api/developer/keys`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newKeyName || null }),
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const json = await res.json();
      setFreshKey(json.key);
      setNewKeyName('');
      await fetchKeys();
    } catch (e: any) {
      setError(e.message ?? 'Failed to create key.');
    } finally {
      setCreating(false);
    }
  };

  const revokeKey = async (id: number) => {
    if (!window.confirm('Revoke this key? Any MCP client using it will stop working.')) return;
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE_URL}/api/developer/keys/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      await fetchKeys();
    } catch (e: any) {
      setError(e.message ?? 'Failed to revoke key.');
    }
  };

  const copySnippet = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-bg text-text-primary">
        <Header />
        <div className="flex items-center justify-center h-64">
          <div className="h-8 w-8 border-2 border-text-primary border-t-transparent animate-spin" />
        </div>
      </div>
    );
  }

  if (!isSignedIn) {
    return (
      <div className="min-h-screen bg-bg text-text-primary">
        <Header />
        <div className="max-w-[860px] mx-auto px-6 py-24">
          <div className="flex flex-col gap-2 mb-6">
            <span className="block w-8 h-px bg-text-tertiary" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-text-secondary">
              Sign in required
            </span>
          </div>
          <h2 className="font-serif text-3xl text-text-primary mb-3">
            Sign in to manage API keys.
          </h2>
          <p className="font-mono text-xs text-text-tertiary mb-8 max-w-sm">
            API keys connect the internship MCP server to your account.
          </p>
          <SignInButton mode="modal">
            <button className="inline-block bg-text-primary text-bg px-5 py-2.5 font-mono text-xs tracking-wide hover:opacity-80 transition-opacity focus:outline-none focus-visible:ring-2 focus-visible:ring-text-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg">
              Sign in →
            </button>
          </SignInButton>
        </div>
      </div>
    );
  }

  const origin = currentOrigin();
  const setup = getMcpSetup(client, mode, freshKey, origin);
  const selectedClient = getMcpClient(client);
  const selectedMode = getMcpMode(mode);

  return (
    <div className="min-h-screen bg-bg text-text-primary">
      <Header />
      <main className="max-w-[860px] mx-auto px-6 py-12">
        <div className="mb-10 pb-6 border-b border-lp-border">
          <div className="flex flex-col gap-2 mb-4">
            <span className="block w-8 h-px bg-text-tertiary" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-text-secondary">
              Account / Developer
            </span>
          </div>
          <h1 className="font-serif text-3xl text-text-primary">API keys.</h1>
          <p className="font-mono text-xs text-text-tertiary mt-2 max-w-lg">
            Connect any MCP agent — Claude Code, Cursor, Codex, Windsurf, Cline — to the
            apply agent. Your agent does the thinking; these keys only fetch jobs, run
            deterministic scoring, and (optionally) compile PDFs.
          </p>
        </div>

        {error && (
          <div className="border border-red-500/40 bg-red-500/5 px-4 py-3 mb-8 font-mono text-xs text-red-500">
            {error}
          </div>
        )}

        {/* Create key */}
        <section className="mb-12">
          <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-4">
            Create a key
          </div>
          <div className="flex gap-3">
            <input
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="Key name (optional, e.g. “laptop / cursor”)"
              className="flex-1 bg-surface border border-lp-border px-4 py-2.5 font-mono text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus-visible:ring-1 focus-visible:ring-text-primary"
            />
            <button
              onClick={createKey}
              disabled={creating}
              className="bg-text-primary text-bg px-5 py-2.5 font-mono text-xs tracking-wide hover:opacity-80 transition-opacity disabled:opacity-40"
            >
              {creating ? 'Creating…' : 'Generate key →'}
            </button>
          </div>

          {freshKey && (
            <div className="mt-4 border border-lp-border bg-surface p-4">
              <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-2">
                Your new key — shown once, copy it now
              </div>
              <div className="flex items-center gap-3">
                <code className="flex-1 font-mono text-xs text-text-primary break-all select-all">
                  {freshKey}
                </code>
                <button
                  onClick={() => copySnippet(freshKey)}
                  className="border border-lp-border px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-text-secondary hover:text-text-primary transition-colors"
                >
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
            </div>
          )}
        </section>

        {/* Key list */}
        <section className="mb-12">
          <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-4">
            Active keys
          </div>
          {loading ? (
            <div className="flex items-center justify-center h-24">
              <div className="h-6 w-6 border-2 border-text-primary border-t-transparent animate-spin" />
            </div>
          ) : keys.length === 0 ? (
            <p className="font-mono text-xs text-text-tertiary">No keys yet.</p>
          ) : (
            <div className="border border-lp-border divide-y divide-lp-border">
              {keys.map((k) => (
                <div key={k.id} className="flex items-center gap-4 px-4 py-3">
                  <code className="font-mono text-xs text-text-primary">{k.key_prefix}…</code>
                  <span className="font-mono text-xs text-text-secondary flex-1 truncate">
                    {k.name || 'unnamed'}
                  </span>
                  <span className="font-mono text-[10px] text-text-tertiary hidden sm:block">
                    created {formatDate(k.created_at)}
                  </span>
                  <span className="font-mono text-[10px] text-text-tertiary hidden sm:block">
                    last used {formatDate(k.last_used)}
                  </span>
                  <button
                    onClick={() => revokeKey(k.id)}
                    className="font-mono text-[10px] uppercase tracking-widest text-red-500/80 hover:text-red-500 transition-colors"
                  >
                    Revoke
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Remote compile usage (API-key quota) */}
        {usage?.remote_compile && (
          <section className="mb-12">
            <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-4">
              Remote compile usage
            </div>
            <div className="border border-lp-border bg-surface p-5">
              <div className="flex items-baseline gap-1.5 mb-3">
                <span className={`font-serif text-3xl leading-none ${
                  usage.remote_compile.remaining === 0 ? 'text-red-500' : 'text-text-primary'
                }`}>
                  {usage.remote_compile.used}
                </span>
                <span className="font-mono text-sm text-text-tertiary">
                  / {usage.remote_compile.limit} this week
                </span>
              </div>
              <div className="w-full h-px bg-lp-border mb-4 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    usage.remote_compile.remaining === 0 ? 'bg-red-500' : 'bg-text-primary'
                  }`}
                  style={{ width: `${Math.min((usage.remote_compile.used / usage.remote_compile.limit) * 100, 100)}%` }}
                />
              </div>
              <p className="font-mono text-[11px] leading-relaxed text-text-tertiary">
                Counts resume compiles your <span className="text-text-secondary">API keys</span> run
                on our servers when the full agent falls back to remote compile. Installing TeX locally
                makes compiles unlimited and keeps them off our servers. Also shown on the{' '}
                <a href="/usage" className="underline hover:text-text-primary">Usage page</a>.
              </p>
            </div>
          </section>
        )}

        {/* Config snippets */}
        <section className="mb-12">
          <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-4">
            Connect your agent
          </div>

          <div className="flex flex-wrap gap-3 mb-4">
            <McpSetupDropdown
              label="Client"
              value={client}
              items={CLIENT_DROPDOWN_ITEMS}
              onChange={setClient}
            />
            <McpSetupDropdown
              label="Mode"
              value={mode}
              items={MODE_DROPDOWN_ITEMS}
              onChange={setMode}
            />
          </div>

          <div className="flex flex-wrap gap-2 mb-4">
            {MCP_MODES.map((m) => (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={`px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest border transition-colors ${
                  mode === m.id
                    ? 'border-text-primary text-text-primary'
                    : 'border-lp-border text-text-tertiary hover:text-text-secondary'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          <div className="border border-lp-border bg-surface p-4 mb-3">
            <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-2">
              {selectedClient.label} / {selectedMode.label}
            </div>
            <p className="font-mono text-[11px] leading-relaxed text-text-secondary mb-2">
              {setup.capability}
            </p>
            <p className="font-mono text-[10px] text-text-tertiary">
              {mode === 'hosted' ? 'Use this command or config in your client.' : (
                <>Save to <span className="text-text-secondary">{setup.configPath}</span>.</>
              )}
            </p>
          </div>

          <p className="font-mono text-[10px] text-text-tertiary mb-2">
            {setup.notes.join(' ')}
          </p>

          <CodeSnippet
            title={client === 'codex' ? '~/.codex/config.toml' : 'MCP configuration'}
            subtitle={selectedMode.label}
            code={setup.snippet}
            copyText={setup.snippet}
            className="mb-3"
          />
          {!freshKey && (
            <p className="font-mono text-[10px] text-text-tertiary mt-2">
              Generate a key above and it will be filled into the snippet automatically.
            </p>
          )}
          {client === 'codex' && mode !== 'hosted' && (
            <p className="font-mono text-[10px] text-text-tertiary mt-2">
              Codex uses <code className="code-inline text-text-secondary">~/.codex/config.toml</code>,
              not a project <code className="code-inline text-text-secondary">.mcp.json</code>. Restart
              Codex after saving, or use <code className="code-inline text-text-secondary">codex mcp add</code>
              from the full docs.
            </p>
          )}
          {mode === 'hosted' && (
            <p className="font-mono text-[10px] text-text-tertiary mt-2">
              Keep hosted keys disposable. If your connector supports headers, prefer
              <code className="code-inline text-text-secondary"> X-API-Key</code>; otherwise use the URL
              key for testing and revoke it when done.
            </p>
          )}
        </section>

        {/* Disclaimer */}
        <section className="pt-6 border-t border-lp-border">
          <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-3">
            Terms of use
          </div>
          <p className="font-mono text-[11px] leading-relaxed text-text-tertiary max-w-2xl">
            The apply agent assists with applications you direct. You are responsible for
            reviewing every application before submission, for the truthfulness of all
            answers, and for complying with each job board's terms of service. Automated
            submission (v2) is opt-in, capped per session, and logged. Your applicant
            profile and EEO answers are stored encrypted on your machine and are never
            sent to our servers. Rate limits apply per key: jobs and prefilter 120/hour,
            remote compile 15/week.
          </p>
        </section>
      </main>
    </div>
  );
};

export default DeveloperPage;
