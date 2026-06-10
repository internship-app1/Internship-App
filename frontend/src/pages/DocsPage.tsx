import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';

/* ------------------------------------------------------------------ */
/* Docs design system — Convex-style readability:                      */
/* sans-serif body at 15-16px with relaxed leading, sticky sidebar     */
/* navigation, clear heading hierarchy. Monospace is reserved for      */
/* code only.                                                          */
/* ------------------------------------------------------------------ */

const Para: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="font-sans text-[15px] leading-7 text-text-secondary mb-4 max-w-[680px]">
    {children}
  </p>
);

const H2: React.FC<{ id: string; children: React.ReactNode }> = ({ id, children }) => (
  <h2 id={id} className="font-sans text-2xl font-semibold text-text-primary mb-4 pt-2 scroll-mt-24">
    {children}
  </h2>
);

const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h3 className="font-sans text-lg font-semibold text-text-primary mt-8 mb-3">
    {children}
  </h3>
);

const CodeBlock: React.FC<{ children: string; title?: string }> = ({ children, title }) => (
  <div className="rounded-lg border border-lp-border overflow-hidden mb-5 max-w-[680px]">
    {title && (
      <div className="px-4 py-2 bg-surface border-b border-lp-border font-mono text-[11px] text-text-tertiary">
        {title}
      </div>
    )}
    <pre className="bg-surface overflow-x-auto p-4 font-mono text-[12.5px] leading-relaxed text-text-secondary">
      {children}
    </pre>
  </div>
);

const InlineCode: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <code className="font-mono text-[13px] text-text-primary bg-surface border border-lp-border rounded px-1.5 py-0.5">
    {children}
  </code>
);

const StepList: React.FC<{ steps: React.ReactNode[] }> = ({ steps }) => (
  <ol className="mb-5 max-w-[680px] space-y-3">
    {steps.map((step, i) => (
      <li key={i} className="flex gap-3">
        <span className="shrink-0 w-6 h-6 rounded-full bg-surface border border-lp-border flex items-center justify-center font-sans text-[12px] font-semibold text-text-primary mt-0.5">
          {i + 1}
        </span>
        <span className="font-sans text-[15px] leading-7 text-text-secondary">{step}</span>
      </li>
    ))}
  </ol>
);

interface EndpointProps {
  method: 'GET' | 'POST';
  path: string;
  limit: string;
  children: React.ReactNode;
}

const Endpoint: React.FC<EndpointProps> = ({ method, path, limit, children }) => (
  <div className="rounded-lg border border-lp-border mb-8 max-w-[680px]">
    <div className="flex items-center gap-3 px-4 py-3 border-b border-lp-border bg-surface rounded-t-lg">
      <span className={`font-mono text-[11px] font-bold px-2 py-0.5 rounded ${
        method === 'GET'
          ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
          : 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
      }`}>
        {method}
      </span>
      <code className="font-mono text-[13px] text-text-primary flex-1">{path}</code>
      <span className="font-sans text-xs text-text-tertiary hidden sm:block">{limit}</span>
    </div>
    <div className="p-5">{children}</div>
  </div>
);

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

const NAV = [
  ['overview', 'Overview'],
  ['authentication', 'Authentication'],
  ['mcp-for-agents', 'MCP for Agents'],
  ['endpoints', 'API Reference'],
  ['errors', 'Errors & Rate Limits'],
] as const;

const DocsPage: React.FC = () => {
  const [active, setActive] = useState<string>('overview');

  // Highlight the sidebar item for the section currently in view
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActive(entry.target.id);
            break;
          }
        }
      },
      { rootMargin: '-20% 0px -70% 0px' },
    );
    NAV.forEach(([id]) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  return (
    <div className="min-h-screen bg-bg text-text-primary">
      <Header />
      <div className="max-w-[1100px] mx-auto px-6 py-10 lg:flex lg:gap-12">
        {/* Sidebar */}
        <aside className="hidden lg:block w-56 shrink-0">
          <nav className="sticky top-10">
            <div className="font-sans text-xs font-semibold uppercase tracking-wide text-text-tertiary mb-3">
              Documentation
            </div>
            <ul className="space-y-0.5 border-l border-lp-border">
              {NAV.map(([id, label]) => (
                <li key={id}>
                  <a
                    href={`#${id}`}
                    className={`block pl-4 -ml-px py-1.5 font-sans text-[14px] border-l transition-colors ${
                      active === id
                        ? 'border-text-primary text-text-primary font-medium'
                        : 'border-transparent text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    {label}
                  </a>
                </li>
              ))}
            </ul>
            <a
              href="/api/v1/openapi.json"
              target="_blank"
              rel="noreferrer"
              className="mt-6 block font-sans text-[13px] text-text-tertiary hover:text-text-primary transition-colors"
            >
              OpenAPI spec ↗
            </a>
            <a
              href="https://github.com/internship-app1/internship-mcp-server"
              target="_blank"
              rel="noreferrer"
              className="mt-2 block font-sans text-[13px] text-text-tertiary hover:text-text-primary transition-colors"
            >
              MCP server on GitHub ↗
            </a>
          </nav>
        </aside>

        {/* Content */}
        <main className="flex-1 min-w-0">
          {/* Page header */}
          <div className="mb-10 pb-8 border-b border-lp-border">
            <h1 className="font-sans text-3xl font-bold text-text-primary mb-3">Documentation</h1>
            <p className="font-sans text-[16px] leading-7 text-text-secondary max-w-[680px]">
              Everything you need to point an MCP agent — or your own code — at the
              Internship Matcher data plane: authentication, agent setup, and the full
              API reference.
            </p>
            {/* Mobile nav */}
            <nav className="flex flex-wrap gap-2 mt-6 lg:hidden">
              {NAV.map(([id, label]) => (
                <a
                  key={id}
                  href={`#${id}`}
                  className="px-3 py-1.5 rounded-full font-sans text-[13px] border border-lp-border text-text-secondary hover:text-text-primary hover:border-text-primary transition-colors"
                >
                  {label}
                </a>
              ))}
            </nav>
          </div>

          {/* -------------------------------------------------------- */}
          <section className="mb-14">
            <H2 id="overview">Overview</H2>
            <Para>
              The Internship Matcher API is a small, deterministic data plane: it serves
              fresh internship postings, runs mechanical keyword and metadata scoring,
              and — as an opt-in fallback — compiles resume JSON into a single-page PDF.
              It's designed to be driven by an AI agent over the{' '}
              <a className="text-text-primary underline underline-offset-2 hover:opacity-70" href="https://modelcontextprotocol.io" target="_blank" rel="noreferrer">
                Model Context Protocol
              </a>{' '}
              via our open-source{' '}
              <a className="text-text-primary underline underline-offset-2 hover:opacity-70" href="https://github.com/internship-app1/internship-mcp-server" target="_blank" rel="noreferrer">
                internship-mcp server
              </a>.
            </Para>
            <Para>
              One thing this API deliberately does <strong className="text-text-primary">not</strong> do:
              think. There is no model behind any endpoint. Ranking judgment, resume
              rewriting, and answering application questions are your agent's job — the
              API only supplies data and deterministic computation. Your applicant
              profile, EEO answers, and raw resume never touch our servers; they stay
              encrypted on your machine inside the MCP server's local vault.
            </Para>
            <Para>
              The machine-readable contract lives at{' '}
              <a className="text-text-primary underline underline-offset-2 hover:opacity-70" href="/api/v1/openapi.json" target="_blank" rel="noreferrer">
                /api/v1/openapi.json
              </a>.
            </Para>
          </section>

          {/* -------------------------------------------------------- */}
          <section className="mb-14">
            <H2 id="authentication">Authentication</H2>
            <Para>
              Every <InlineCode>/api/v1</InlineCode> request needs a per-user API key in
              the <InlineCode>X-API-Key</InlineCode> header. Generate one on the{' '}
              <Link to="/developer" className="text-text-primary underline underline-offset-2 hover:opacity-70">
                Developer page
              </Link>{' '}
              — it's shown once, looks like <InlineCode>im_live_…</InlineCode>, and can
              be revoked there at any time. Only a hash is stored on our side.
            </Para>
            <CodeBlock title="curl">{`curl -H "X-API-Key: im_live_..." \\
  "https://internship-app-production.up.railway.app/api/v1/jobs?limit=5"`}</CodeBlock>
            <Para>
              If you use the MCP server you never send this header yourself — the server
              reads <InlineCode>INTERNSHIP_API_KEY</InlineCode> from its environment and
              attaches it to every backend call.
            </Para>
          </section>

          {/* -------------------------------------------------------- */}
          <section className="mb-14">
            <H2 id="mcp-for-agents">MCP for Agents</H2>
            <Para>
              The fastest way to use this API is to not call it directly: install the
              MCP server in your agent (Claude Code, Cursor, Codex, Windsurf, Cline) and
              let the agent drive.
            </Para>
            <StepList
              steps={[
                <>
                  Sign in and generate an API key on the{' '}
                  <Link to="/developer" className="text-text-primary underline underline-offset-2 hover:opacity-70">
                    Developer page
                  </Link>.
                </>,
                <>
                  Add the server to your client config — the Developer page renders a
                  ready-to-paste snippet for your exact client and transport. Docker is
                  recommended (resume PDFs compile locally, fully private); uvx is the
                  zero-install quick start.
                </>,
                <>Ask your agent to get to work.</>,
              ]}
            />
            <CodeBlock title=".mcp.json (Claude Code) · ~/.cursor/mcp.json (Cursor) — Docker, recommended">{`{
  "mcpServers": {
    "internship": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-v", "internship-home:/root/.internship-agent",
               "-e", "INTERNSHIP_API_KEY",
               "ghcr.io/internship-app1/internship-mcp-server:latest"],
      "env": { "INTERNSHIP_API_KEY": "im_live_..." }
    },
    "playwright": { "command": "npx", "args": ["@playwright/mcp@latest"] }
  }
}`}</CodeBlock>
            <Para>
              The Playwright MCP is a separate, official server your agent uses to
              prefill application forms in your browser — you always review and hit
              submit yourself.
            </Para>
            <H3>What your agent can do</H3>
            <Para>
              Once connected, the agent gets 15 tools: profile setup with encrypted
              local storage, resume parsing, <InlineCode>jobs_list</InlineCode> /{' '}
              <InlineCode>job_get</InlineCode> / <InlineCode>jobs_prefilter</InlineCode>,
              local PDF compilation with widow diagnostics, application-packet assembly
              with an authentic-answer guardrail, and a local application tracker. A
              good first prompt:
            </Para>
            <CodeBlock title="First prompt">{`Set up my internship profile, then find postings from the last 3 days
that fit my resume at ~/resume.pdf, tailor my resume for the top 5,
and prefill the applications for my review.`}</CodeBlock>
          </section>

          {/* -------------------------------------------------------- */}
          <section className="mb-14">
            <H2 id="endpoints">API Reference</H2>
            <Para>
              All endpoints live under <InlineCode>/api/v1</InlineCode> and require the{' '}
              <InlineCode>X-API-Key</InlineCode> header. Rate limits are per key.
            </Para>

            <Endpoint method="GET" path="/api/v1/jobs" limit="120 / hour">
              <Para>
                List active internship postings, freshest first. Filter with{' '}
                <InlineCode>since_hours</InlineCode> (only jobs first seen in the last N
                hours), <InlineCode>max_days_old</InlineCode> (default 30),{' '}
                <InlineCode>location</InlineCode>, free-text <InlineCode>q</InlineCode>,
                and page with <InlineCode>limit</InlineCode> (max 500) /{' '}
                <InlineCode>offset</InlineCode>.
              </Para>
              <CodeBlock title="Response">{`{ "jobs": [{ "job_hash": "9b43…", "company": "Tesla",
    "title": "Software Engineer Intern", "location": "Palo Alto, CA",
    "apply_link": "https://…", "required_skills": ["Python", "React"],
    "days_since_posted": 0, "date_posted": "2026-06-09",
    "description_preview": "First 500 chars…" }],
  "total": 147, "limit": 200, "offset": 0 }`}</CodeBlock>
            </Endpoint>

            <Endpoint method="GET" path="/api/v1/jobs/{job_hash}" limit="120 / hour">
              <Para>
                One job with its full, untruncated description and requirements — what
                an agent fetches before rewriting a resume for the role. Returns{' '}
                <InlineCode>404</InlineCode> for an unknown hash.
              </Para>
            </Endpoint>

            <Endpoint method="POST" path="/api/v1/jobs/prefilter" limit="120 / hour">
              <Para>
                Deterministic scoring of the job pool against a small, PII-free profile.
                Returns the top <InlineCode>target_count</InlineCode> candidates with
                keyword, metadata, and combined scores, matched/missing skills, and a{' '}
                <InlineCode>hard_filter_passed</InlineCode> flag (senior-role and
                years-required exclusions). The scoring is mechanical — treat it as a
                prefilter and let your agent do the real ranking.
              </Para>
              <CodeBlock title="Request">{`{ "resume_profile": {
    "skills": ["python", "react"],
    "experience_level": "student",        // student | entry_level | experienced
    "years_of_experience": 1,
    "location": "Boston, MA",
    "willing_to_relocate": true,
    "remote_ok": true },
  "filters": { "since_hours": 72 },
  "target_count": 40 }`}</CodeBlock>
              <CodeBlock title="Response">{`{ "candidates": [{ "job_hash": "…", "company": "…", "title": "…",
    "keyword_score": 78, "metadata_score": 64, "combined_score": 74,
    "skill_matches": ["python", "react"], "skill_gaps": ["go"],
    "hard_filter_passed": true, "description_preview": "…" }],
  "evaluated": 147, "returned": 40 }`}</CodeBlock>
            </Endpoint>

            <Endpoint method="POST" path="/api/v1/resume/compile" limit="60 / day · 3 concurrent">
              <Para>
                Fallback PDF compiler for environments without local TeX (the Docker MCP
                image compiles locally and never calls this). Takes resume JSON, returns
                a base64 PDF plus diagnostics your agent uses to fix layout: page count,
                the locked font size, spacing preset, page fill ratio, and a list of{' '}
                <InlineCode>widows</InlineCode> — bullets whose last line is nearly
                empty and should be rewritten.
              </Para>
              <CodeBlock title="Request">{`{ "resume_json": { "name": "…", "email": "…", "experience": [...],
    "education": [...], "skills": {"Languages": "Python, Go"}, "projects": [...] },
  "options": { "font_anchor": 11, "spacing": "tight" } }`}</CodeBlock>
              <CodeBlock title="Response">{`{ "pdf_base64": "…",
  "diagnostics": { "pages": 1, "font_size": 11, "spacing": "normal",
    "fill_ratio": 0.91,
    "widows": [{ "section": "experience", "entry": 1, "bullet": 2,
                 "last_line_chars": 18 }] } }`}</CodeBlock>
              <Para>
                Over-capacity requests are rejected immediately with{' '}
                <InlineCode>429</InlineCode> and a <InlineCode>Retry-After</InlineCode>{' '}
                header rather than queued. Identical payloads are served from a content
                cache.
              </Para>
            </Endpoint>
          </section>

          {/* -------------------------------------------------------- */}
          <section className="mb-6">
            <H2 id="errors">Errors &amp; Rate Limits</H2>
            <div className="rounded-lg border border-lp-border divide-y divide-lp-border mb-5 max-w-[680px]">
              {[
                ['401', 'Missing, invalid, or revoked API key. Regenerate on the Developer page.'],
                ['404', 'Unknown job_hash.'],
                ['422', 'Request body failed validation — e.g. experience_level must be exactly student, entry_level, or experienced.'],
                ['429', 'Rate limit exceeded, or all compile slots busy (check Retry-After). Compile locally via Docker to avoid compile limits entirely.'],
              ].map(([code, desc]) => (
                <div key={code} className="flex gap-4 px-4 py-3">
                  <code className="font-mono text-[13px] font-semibold text-text-primary w-10 shrink-0">{code}</code>
                  <span className="font-sans text-[14px] leading-6 text-text-secondary">{desc}</span>
                </div>
              ))}
            </div>
            <Para>
              Limits are per API key: jobs and prefilter at 120 requests/hour, remote
              compile at 60/day with 3 concurrent slots. The MCP server surfaces these
              as legible errors to your agent and backs off automatically on network
              failures.
            </Para>
          </section>
        </main>
      </div>
    </div>
  );
};

export default DocsPage;
