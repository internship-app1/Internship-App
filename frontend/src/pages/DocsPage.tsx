import React from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';

/* ------------------------------------------------------------------ */
/* Small presentational helpers (match the editorial design language)  */
/* ------------------------------------------------------------------ */

const SectionLabel: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary mb-4">
    {children}
  </div>
);

const CodeBlock: React.FC<{ children: string }> = ({ children }) => (
  <pre className="border border-lp-border bg-surface overflow-x-auto p-4 font-mono text-[11px] leading-relaxed text-text-secondary mb-4">
    {children}
  </pre>
);

const Para: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="font-mono text-xs leading-relaxed text-text-secondary mb-4 max-w-2xl">
    {children}
  </p>
);

const InlineCode: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <code className="text-text-primary bg-surface border border-lp-border px-1 py-0.5 text-[11px]">
    {children}
  </code>
);

interface EndpointProps {
  method: 'GET' | 'POST';
  path: string;
  limit: string;
  children: React.ReactNode;
}

const Endpoint: React.FC<EndpointProps> = ({ method, path, limit, children }) => (
  <div className="border border-lp-border mb-6">
    <div className="flex items-center gap-3 px-4 py-3 border-b border-lp-border bg-surface">
      <span className={`font-mono text-[10px] uppercase tracking-widest px-2 py-1 border ${
        method === 'GET' ? 'border-text-tertiary text-text-secondary' : 'border-text-primary text-text-primary'
      }`}>
        {method}
      </span>
      <code className="font-mono text-xs text-text-primary flex-1">{path}</code>
      <span className="font-mono text-[10px] text-text-tertiary hidden sm:block">{limit}</span>
    </div>
    <div className="p-4">{children}</div>
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
  return (
    <div className="min-h-screen bg-bg text-text-primary">
      <Header />
      <main className="max-w-[860px] mx-auto px-6 py-12">
        {/* Page header */}
        <div className="mb-10 pb-6 border-b border-lp-border">
          <div className="flex flex-col gap-2 mb-4">
            <span className="block w-8 h-px bg-text-tertiary" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-text-secondary">
              Documentation
            </span>
          </div>
          <h1 className="font-serif text-3xl text-text-primary">API &amp; MCP docs.</h1>
          <p className="font-mono text-xs text-text-tertiary mt-2 max-w-lg">
            Everything you need to point an MCP agent — or your own code — at the
            Internship Matcher data plane.
          </p>
          {/* In-page nav */}
          <nav className="flex flex-wrap gap-2 mt-6">
            {NAV.map(([id, label]) => (
              <a
                key={id}
                href={`#${id}`}
                className="px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest border border-lp-border text-text-tertiary hover:text-text-primary hover:border-text-primary transition-colors"
              >
                {label}
              </a>
            ))}
          </nav>
        </div>

        {/* ---------------------------------------------------------- */}
        <section id="overview" className="mb-14">
          <SectionLabel>Overview</SectionLabel>
          <Para>
            The Internship Matcher API is a small, deterministic data plane: it serves
            fresh internship postings, runs mechanical keyword + metadata scoring, and
            (as an opt-in fallback) compiles resume JSON to a single-page PDF. It is
            designed to be driven by an AI agent over the{' '}
            <a className="underline hover:text-text-primary" href="https://modelcontextprotocol.io" target="_blank" rel="noreferrer">
              Model Context Protocol
            </a>{' '}
            via our open-source{' '}
            <a className="underline hover:text-text-primary" href="https://github.com/internship-app1/internship-mcp-server" target="_blank" rel="noreferrer">
              internship-mcp server
            </a>.
          </Para>
          <Para>
            One thing this API deliberately does <em className="not-italic text-text-primary">not</em> do:
            think. There is no model behind any endpoint. Ranking judgment, resume
            rewriting, and answering application questions are your agent's job — the
            API only supplies data and deterministic computation. Your applicant
            profile, EEO answers, and raw resume never touch our servers; they stay
            encrypted on your machine inside the MCP server's local vault.
          </Para>
          <Para>
            The machine-readable contract lives at{' '}
            <a className="underline hover:text-text-primary" href="/api/v1/openapi.json" target="_blank" rel="noreferrer">
              /api/v1/openapi.json
            </a>.
          </Para>
        </section>

        {/* ---------------------------------------------------------- */}
        <section id="authentication" className="mb-14">
          <SectionLabel>Authentication</SectionLabel>
          <Para>
            Every <InlineCode>/api/v1</InlineCode> request needs a per-user API key in the{' '}
            <InlineCode>X-API-Key</InlineCode> header. Generate one on the{' '}
            <Link to="/developer" className="underline hover:text-text-primary">Developer page</Link>{' '}
            — it is shown once, looks like <InlineCode>im_live_…</InlineCode>, and can be
            revoked there at any time. Only a hash is stored on our side.
          </Para>
          <CodeBlock>{`curl -H "X-API-Key: im_live_..." \\
  "https://internship-app-production.up.railway.app/api/v1/jobs?limit=5"`}</CodeBlock>
          <Para>
            If you use the MCP server you never send this header yourself — the server
            reads <InlineCode>INTERNSHIP_API_KEY</InlineCode> from its environment and
            attaches it to every backend call.
          </Para>
        </section>

        {/* ---------------------------------------------------------- */}
        <section id="mcp-for-agents" className="mb-14">
          <SectionLabel>MCP for Agents — quick setup</SectionLabel>
          <Para>
            The fastest way to use this API is to not call it directly: install the MCP
            server in your agent (Claude Code, Cursor, Codex, Windsurf, Cline) and let
            the agent drive. Three steps:
          </Para>
          <Para>
            <span className="text-text-primary">1.</span> Sign in and generate an API key on the{' '}
            <Link to="/developer" className="underline hover:text-text-primary">Developer page</Link>.
            <br />
            <span className="text-text-primary">2.</span> Add the server to your client config —
            the Developer page renders a ready-to-paste snippet for your exact client and
            transport. Docker is recommended (resume PDFs compile locally, fully private);
            uvx is the zero-install quick start.
            <br />
            <span className="text-text-primary">3.</span> Ask your agent to get to work.
          </Para>
          <CodeBlock>{`// .mcp.json (Claude Code) / ~/.cursor/mcp.json (Cursor) — Docker, recommended
{
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
            The Playwright MCP is a separate, official server your agent uses to prefill
            application forms in your browser — you always review and hit submit yourself.
          </Para>
          <Para>
            Once connected, the agent gets 15 tools: profile setup &amp; encrypted local
            storage, resume parsing, <InlineCode>jobs_list</InlineCode> /{' '}
            <InlineCode>job_get</InlineCode> / <InlineCode>jobs_prefilter</InlineCode>,
            local PDF compilation with widow diagnostics, application-packet assembly
            with an authentic-answer guardrail, and a local application tracker. A good
            first prompt:
          </Para>
          <CodeBlock>{`Set up my internship profile, then find postings from the last 3 days
that fit my resume at ~/resume.pdf, tailor my resume for the top 5,
and prefill the applications for my review.`}</CodeBlock>
        </section>

        {/* ---------------------------------------------------------- */}
        <section id="endpoints" className="mb-14">
          <SectionLabel>API Reference — /api/v1</SectionLabel>

          <Endpoint method="GET" path="/api/v1/jobs" limit="120 / hour">
            <Para>
              List active internship postings, freshest first. Filter with{' '}
              <InlineCode>since_hours</InlineCode> (only jobs first seen in the last N
              hours), <InlineCode>max_days_old</InlineCode> (default 30),{' '}
              <InlineCode>location</InlineCode>, free-text <InlineCode>q</InlineCode>, and
              page with <InlineCode>limit</InlineCode> (max 500) / <InlineCode>offset</InlineCode>.
            </Para>
            <CodeBlock>{`{ "jobs": [{ "job_hash": "9b43…", "company": "Tesla",
    "title": "Software Engineer Intern", "location": "Palo Alto, CA",
    "apply_link": "https://…", "required_skills": ["Python", "React"],
    "days_since_posted": 0, "date_posted": "2026-06-09",
    "description_preview": "First 500 chars…" }],
  "total": 147, "limit": 200, "offset": 0 }`}</CodeBlock>
          </Endpoint>

          <Endpoint method="GET" path="/api/v1/jobs/{job_hash}" limit="120 / hour">
            <Para>
              One job with its full, untruncated description and requirements — what an
              agent fetches before rewriting a resume for the role. Returns{' '}
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
            <CodeBlock>{`// request
{ "resume_profile": {
    "skills": ["python", "react"],
    "experience_level": "student",        // student | entry_level | experienced
    "years_of_experience": 1,
    "location": "Boston, MA",
    "willing_to_relocate": true,
    "remote_ok": true },
  "filters": { "since_hours": 72 },
  "target_count": 40 }

// response
{ "candidates": [{ "job_hash": "…", "company": "…", "title": "…",
    "keyword_score": 78, "metadata_score": 64, "combined_score": 74,
    "skill_matches": ["python", "react"], "skill_gaps": ["go"],
    "hard_filter_passed": true, "description_preview": "…" }],
  "evaluated": 147, "returned": 40 }`}</CodeBlock>
          </Endpoint>

          <Endpoint method="POST" path="/api/v1/resume/compile" limit="60 / day · 3 concurrent">
            <Para>
              Fallback PDF compiler for environments without local TeX (the Docker MCP
              image compiles locally and never calls this). Takes resume JSON, returns a
              base64 PDF plus diagnostics your agent uses to fix layout: page count, the
              locked font size, spacing preset, page fill ratio, and a list of{' '}
              <InlineCode>widows</InlineCode> — bullets whose last line is nearly empty
              and should be rewritten.
            </Para>
            <CodeBlock>{`// request
{ "resume_json": { "name": "…", "email": "…", "experience": [...],
    "education": [...], "skills": {"Languages": "Python, Go"}, "projects": [...] },
  "options": { "font_anchor": 11, "spacing": "tight" } }

// response
{ "pdf_base64": "…",
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

        {/* ---------------------------------------------------------- */}
        <section id="errors" className="mb-2">
          <SectionLabel>Errors &amp; rate limits</SectionLabel>
          <div className="border border-lp-border divide-y divide-lp-border mb-4">
            {[
              ['401', 'Missing, invalid, or revoked API key. Regenerate on the Developer page.'],
              ['404', 'Unknown job_hash.'],
              ['422', 'Request body failed validation — e.g. experience_level must be exactly student, entry_level, or experienced.'],
              ['429', 'Rate limit exceeded, or all compile slots busy (check Retry-After). Compile locally via Docker to avoid compile limits entirely.'],
            ].map(([code, desc]) => (
              <div key={code} className="flex gap-4 px-4 py-3">
                <code className="font-mono text-xs text-text-primary w-8 shrink-0">{code}</code>
                <span className="font-mono text-xs text-text-secondary">{desc}</span>
              </div>
            ))}
          </div>
          <Para>
            Limits are per API key: jobs and prefilter at 120 requests/hour, remote
            compile at 60/day with 3 concurrent slots. The MCP server surfaces these as
            legible errors to your agent and backs off automatically on network failures.
          </Para>
        </section>
      </main>
    </div>
  );
};

export default DocsPage;
