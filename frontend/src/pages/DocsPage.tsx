import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import CodeSnippet from '../components/CodeSnippet';
import McpSetupDropdown from '../components/McpSetupDropdown';
import OnThisPage, { TocItem } from '../components/docs/OnThisPage';
import { useResolvedTheme } from '../components/theme-provider';
import { CLIENT_DROPDOWN_ITEMS, MODE_DROPDOWN_ITEMS } from '../lib/mcpDropdownItems';
import { AGENT_WORKFLOW_EXAMPLES } from '../data/agentWorkflowExamples';
import {
  getMcpClient,
  getMcpMode,
  getMcpSetup,
  McpClientId,
  McpSetupMode,
} from '../data/mcpSetup';

/* ------------------------------------------------------------------ */
/* Docs design system — Convex-style readability + Intercom-style      */
/* API reference: language-selectable request samples and field-by-    */
/* field schema tables with type/required badges and blurbs.           */
/* ------------------------------------------------------------------ */

const API_BASE = 'https://internship-app-production.up.railway.app';

function currentOrigin(): string {
  return typeof window === 'undefined' ? 'https://internshipmatcher.com' : window.location.origin;
}

const Para: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="font-sans text-[15px] leading-7 text-text-secondary mb-4 max-w-[680px]">
    {children}
  </p>
);

const H2: React.FC<{ id: string; children: React.ReactNode }> = ({ id, children }) => (
  <h2 id={id} className="font-sans text-[22px] font-semibold tracking-[-0.01em] text-text-primary mb-4 pt-2 scroll-mt-24">
    {children}
  </h2>
);

const H3: React.FC<{ id?: string; children: React.ReactNode }> = ({ id, children }) => (
  <h3 id={id} className="font-sans text-[16px] font-semibold text-text-primary mt-8 mb-3 scroll-mt-24">
    {children}
  </h3>
);

const SubLabel: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="font-sans text-[13px] font-semibold uppercase tracking-wide text-text-tertiary mt-6 mb-2">
    {children}
  </div>
);

const CodeBlock: React.FC<{ children: string; title?: string; lang?: string }> = ({ children, title, lang }) => (
  <CodeSnippet
    title={title ?? 'Code snippet'}
    code={children}
    language={lang ?? 'bash'}
    className="mb-5 max-w-[680px]"
  />
);

const InlineCode: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <code className="docs-inline-code font-mono text-[13px] border rounded px-1.5 py-0.5">
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

/* ------------------------------------------------------------------ */
/* Language-selectable request samples                                 */
/* ------------------------------------------------------------------ */

type Lang = 'curl' | 'python' | 'javascript';
const LANG_LABELS: Record<Lang, string> = {
  curl: 'cURL',
  python: 'Python',
  javascript: 'JavaScript',
};

interface RequestSampleProps {
  lang: Lang;
  onLangChange: (l: Lang) => void;
  samples: Record<Lang, string>;
}

const RequestSample: React.FC<RequestSampleProps> = ({ lang, onLangChange, samples }) => (
  <div className="mb-5 max-w-[680px]">
    <div className="flex items-center justify-between gap-3 mb-2">
      <div className="font-sans text-[12px] font-semibold uppercase tracking-wide text-text-tertiary">
        Example request
      </div>
      <select
        value={lang}
        onChange={(e) => onLangChange(e.target.value as Lang)}
        aria-label="Example language"
        className="bg-[rgba(255,255,255,0.05)] border border-[color:var(--docs-code-border)] rounded px-2 py-1 font-sans text-[12px] text-[var(--docs-code-text)] focus:outline-none focus-visible:ring-1 focus-visible:ring-text-primary cursor-pointer"
      >
        {(Object.keys(LANG_LABELS) as Lang[]).map((l) => (
          <option key={l} value={l}>{LANG_LABELS[l]}</option>
        ))}
      </select>
    </div>
    <CodeSnippet
      title="Request"
      code={samples[lang]}
      language={lang === 'curl' ? 'bash' : lang}
      className="max-w-[680px]"
    />
  </div>
);

/* ------------------------------------------------------------------ */
/* Field-by-field schema tables                                        */
/* ------------------------------------------------------------------ */

interface FieldDef {
  name: string;
  type: string;
  required?: boolean;
  default?: string;
  desc: React.ReactNode;
  children?: FieldDef[];
}

const FieldRow: React.FC<{ field: FieldDef; depth?: number }> = ({ field, depth = 0 }) => (
  <>
    <div className={`px-4 py-3 ${depth > 0 ? 'bg-bg' : ''}`}>
      <div className="flex flex-wrap items-center gap-2 mb-1" style={{ paddingLeft: depth * 20 }}>
        {depth > 0 && <span className="text-text-tertiary font-mono text-[12px]">↳</span>}
        <code className="font-mono text-[13px] font-semibold text-text-primary">{field.name}</code>
        <span className="font-mono text-[11px] text-text-tertiary bg-surface border border-lp-border rounded px-1.5 py-0.5">
          {field.type}
        </span>
        {field.required && (
          <span className="font-sans text-[10px] font-semibold uppercase tracking-wide text-red-500">
            required
          </span>
        )}
        {field.default !== undefined && (
          <span className="font-mono text-[11px] text-text-tertiary">default: {field.default}</span>
        )}
      </div>
      <p className="font-sans text-[14px] leading-6 text-text-secondary" style={{ paddingLeft: depth * 20 }}>
        {field.desc}
      </p>
    </div>
    {field.children?.map((c) => (
      <FieldRow key={`${field.name}.${c.name}`} field={c} depth={depth + 1} />
    ))}
  </>
);

const FieldTable: React.FC<{ fields: FieldDef[] }> = ({ fields }) => (
  <div className="rounded-lg border border-lp-border divide-y divide-lp-border mb-5 max-w-[680px]">
    {fields.map((f) => (
      <FieldRow key={f.name} field={f} />
    ))}
  </div>
);

interface EndpointProps {
  method: 'GET' | 'POST';
  path: string;
  limit: string;
  children: React.ReactNode;
}

const Endpoint: React.FC<EndpointProps> = ({ method, path, limit, children }) => (
  <div className="rounded-lg border border-lp-border mb-10 max-w-[680px]">
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
/* Request samples per endpoint                                        */
/* ------------------------------------------------------------------ */

const JOBS_SAMPLES: Record<Lang, string> = {
  curl: `curl -H "X-API-Key: im_live_..." \\
  "${API_BASE}/api/v1/jobs?since_hours=72&limit=20"`,
  python: `import requests

resp = requests.get(
    "${API_BASE}/api/v1/jobs",
    headers={"X-API-Key": "im_live_..."},
    params={"since_hours": 72, "limit": 20},
)
resp.raise_for_status()
for job in resp.json()["jobs"]:
    print(job["company"], "—", job["title"])`,
  javascript: `const resp = await fetch(
  "${API_BASE}/api/v1/jobs?since_hours=72&limit=20",
  { headers: { "X-API-Key": "im_live_..." } }
);
if (!resp.ok) throw new Error(\`HTTP \${resp.status}\`);
const { jobs, total } = await resp.json();
jobs.forEach((j) => console.log(j.company, "—", j.title));`,
};

const JOB_DETAIL_SAMPLES: Record<Lang, string> = {
  curl: `curl -H "X-API-Key: im_live_..." \\
  "${API_BASE}/api/v1/jobs/9b43fdc80652dcfe..."`,
  python: `import requests

resp = requests.get(
    "${API_BASE}/api/v1/jobs/9b43fdc80652dcfe...",
    headers={"X-API-Key": "im_live_..."},
)
resp.raise_for_status()
job = resp.json()
print(job["title"], "at", job["company"])
print(job["description"])  # full, untruncated JD`,
  javascript: `const resp = await fetch(
  "${API_BASE}/api/v1/jobs/9b43fdc80652dcfe...",
  { headers: { "X-API-Key": "im_live_..." } }
);
if (!resp.ok) throw new Error(\`HTTP \${resp.status}\`);
const job = await resp.json();
console.log(job.title, "at", job.company);
console.log(job.description); // full, untruncated JD`,
};

const PREFILTER_SAMPLES: Record<Lang, string> = {
  curl: `curl -X POST "${API_BASE}/api/v1/jobs/prefilter" \\
  -H "X-API-Key: im_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "resume_profile": {
      "skills": ["python", "react"],
      "experience_level": "student",
      "years_of_experience": 1,
      "location": "Boston, MA",
      "willing_to_relocate": true,
      "remote_ok": true
    },
    "filters": { "since_hours": 72 },
    "target_count": 40
  }'`,
  python: `import requests

resp = requests.post(
    "${API_BASE}/api/v1/jobs/prefilter",
    headers={"X-API-Key": "im_live_..."},
    json={
        "resume_profile": {
            "skills": ["python", "react"],
            "experience_level": "student",
            "years_of_experience": 1,
            "location": "Boston, MA",
            "willing_to_relocate": True,
            "remote_ok": True,
        },
        "filters": {"since_hours": 72},
        "target_count": 40,
    },
)
resp.raise_for_status()
for c in resp.json()["candidates"]:
    print(c["combined_score"], c["company"], "—", c["title"])`,
  javascript: `const resp = await fetch("${API_BASE}/api/v1/jobs/prefilter", {
  method: "POST",
  headers: {
    "X-API-Key": "im_live_...",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    resume_profile: {
      skills: ["python", "react"],
      experience_level: "student",
      years_of_experience: 1,
      location: "Boston, MA",
      willing_to_relocate: true,
      remote_ok: true,
    },
    filters: { since_hours: 72 },
    target_count: 40,
  }),
});
if (!resp.ok) throw new Error(\`HTTP \${resp.status}\`);
const { candidates } = await resp.json();
candidates.forEach((c) =>
  console.log(c.combined_score, c.company, "—", c.title));`,
};

const COMPILE_SAMPLES: Record<Lang, string> = {
  curl: `curl -X POST "${API_BASE}/api/v1/resume/compile" \\
  -H "X-API-Key: im_live_..." \\
  -H "Content-Type: application/json" \\
  -d @resume.json   # { "resume_json": {...}, "options": {...} }`,
  python: `import base64, requests

resp = requests.post(
    "${API_BASE}/api/v1/resume/compile",
    headers={"X-API-Key": "im_live_..."},
    json={
        "resume_json": resume_json,   # see schema below
        "options": {"font_anchor": 11, "spacing": "tight"},
    },
)
resp.raise_for_status()
body = resp.json()
with open("resume.pdf", "wb") as f:
    f.write(base64.b64decode(body["pdf_base64"]))
print(body["diagnostics"]["widows"])  # bullets to rewrite, if any`,
  javascript: `const resp = await fetch("${API_BASE}/api/v1/resume/compile", {
  method: "POST",
  headers: {
    "X-API-Key": "im_live_...",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    resume_json: resumeJson, // see schema below
    options: { font_anchor: 11, spacing: "tight" },
  }),
});
if (!resp.ok) throw new Error(\`HTTP \${resp.status}\`);
const { pdf_base64, diagnostics } = await resp.json();
await fs.promises.writeFile("resume.pdf", Buffer.from(pdf_base64, "base64"));
console.log(diagnostics.widows); // bullets to rewrite, if any`,
};

/* ------------------------------------------------------------------ */
/* Field definitions                                                   */
/* ------------------------------------------------------------------ */

const JOB_FIELDS: FieldDef[] = [
  { name: 'job_hash', type: 'string', desc: 'Stable unique ID for the posting (SHA-256 of company, title, location, and apply URL). Use it with the other endpoints and for deduplication.' },
  { name: 'company', type: 'string', desc: 'Company name as scraped from the source listing.' },
  { name: 'title', type: 'string', desc: 'Role title, e.g. "Software Engineer Intern".' },
  { name: 'location', type: 'string', desc: 'Location string from the listing — may be a city, "Remote", or multiple options.' },
  { name: 'apply_link', type: 'string', desc: 'Direct URL to the application page (Greenhouse, Lever, Workday, etc.).' },
  { name: 'source', type: 'string', desc: 'Where the job was scraped from (currently github_internships — the SimplifyJobs repo).' },
  { name: 'required_skills', type: 'string[]', desc: 'Skills extracted from the listing. Used by prefilter keyword scoring.' },
  { name: 'days_since_posted', type: 'integer | null', desc: 'Age of the original posting in days. 0 means posted today.' },
  { name: 'date_posted', type: 'string | null', desc: 'Original posting date (YYYY-MM-DD) when the source provides it.' },
  { name: 'description_preview', type: 'string', desc: 'First 500 characters of the job description. Fetch the full text via GET /jobs/{job_hash}.' },
];

const JOBS_QUERY_FIELDS: FieldDef[] = [
  { name: 'since_hours', type: 'integer', desc: 'Only return jobs first seen in the last N hours. Use 72 for "what is new this week-ish"; omit for the full active pool.' },
  { name: 'max_days_old', type: 'integer', default: '30', desc: 'Exclude jobs whose original posting date is older than this many days.' },
  { name: 'location', type: 'string', desc: 'Case-insensitive substring match on the job location, e.g. "remote" or "new york".' },
  { name: 'q', type: 'string', desc: 'Free-text search across title, company, and description.' },
  { name: 'limit', type: 'integer', default: '200', desc: 'Page size. Capped at 500.' },
  { name: 'offset', type: 'integer', default: '0', desc: 'Number of jobs to skip — combine with limit for paging.' },
];

const JOBS_RESPONSE_FIELDS: FieldDef[] = [
  { name: 'jobs', type: 'Job[]', desc: 'The page of matching jobs, freshest first. Each Job has the fields listed below.' },
  { name: 'total', type: 'integer', desc: 'Total number of jobs matching the filters (across all pages).' },
  { name: 'limit', type: 'integer', desc: 'Echo of the page size used.' },
  { name: 'offset', type: 'integer', desc: 'Echo of the offset used.' },
];

const JOB_DETAIL_FIELDS: FieldDef[] = [
  { name: 'description', type: 'string | null', desc: 'The FULL, untruncated job description — what an agent reads before tailoring a resume for the role.' },
  { name: 'job_requirements', type: 'string | null', desc: 'Separately scraped requirements text, when the source provides it.' },
];

const PREFILTER_BODY_FIELDS: FieldDef[] = [
  {
    name: 'resume_profile', type: 'object', required: true,
    desc: 'A small, PII-free summary of the candidate. This is deliberately the only resume-derived data the API accepts — never send raw resume text.',
    children: [
      { name: 'skills', type: 'string[]', required: true, desc: 'Candidate skills, lowercase works best ("python", "react"). Fuzzy-matched against each job\'s required_skills.' },
      { name: 'experience_level', type: 'enum', required: true, desc: <>Exactly one of <InlineCode>student</InlineCode>, <InlineCode>entry_level</InlineCode>, <InlineCode>experienced</InlineCode>. Anything else is a 422.</> },
      { name: 'years_of_experience', type: 'integer', default: '0', desc: 'Years of professional experience. Drives the hard filter — e.g. jobs demanding 5+ years are excluded for candidates under 3.' },
      { name: 'location', type: 'string', desc: 'Home base, e.g. "Boston, MA". Improves the metadata location score.' },
      { name: 'willing_to_relocate', type: 'boolean', default: 'false', desc: 'Whether on-site roles outside the home location should still score well.' },
      { name: 'remote_ok', type: 'boolean', default: 'false', desc: 'Whether remote roles are acceptable — remote-friendly jobs get a location boost.' },
    ],
  },
  {
    name: 'filters', type: 'object',
    desc: 'Optional job-pool filters — same semantics as the GET /jobs query parameters.',
    children: [
      { name: 'since_hours', type: 'integer', desc: 'Only score jobs first seen in the last N hours.' },
      { name: 'max_days_old', type: 'integer', default: '30', desc: 'Exclude postings older than this many days.' },
      { name: 'location', type: 'string', desc: 'Substring filter on job location.' },
      { name: 'q', type: 'string', desc: 'Free-text filter on title/company/description.' },
    ],
  },
  { name: 'target_count', type: 'integer', default: '40', desc: 'How many top candidates to return (max 200).' },
];

const PREFILTER_RESPONSE_FIELDS: FieldDef[] = [
  {
    name: 'candidates', type: 'Candidate[]',
    desc: 'Scored jobs, best first. Jobs that fail the hard filter sort to the bottom rather than disappearing, so your agent can see what was excluded and why.',
    children: [
      { name: 'job_hash', type: 'string', desc: 'Use with GET /jobs/{job_hash} to pull the full description for re-ranking or tailoring.' },
      { name: 'keyword_score', type: 'integer (0–100)', desc: 'Fuzzy skill-coverage score: how many of the job\'s required skills the profile matches, plus small title/role bonuses.' },
      { name: 'metadata_score', type: 'integer (0–100)', desc: 'Weighted compatibility on experience level (40%), location (25%), industry (20%), and work authorization (15%).' },
      { name: 'combined_score', type: 'integer (0–100)', desc: '70% keyword + 30% metadata. Fine for quick mode; for deeper runs, let your agent re-rank from the full JDs.' },
      { name: 'skill_matches', type: 'string[]', desc: 'Required skills the profile covers (fuzzy: "react" matches "React.js").' },
      { name: 'skill_gaps', type: 'string[]', desc: 'Required skills the profile is missing — useful for cover-letter framing or skipping.' },
      { name: 'hard_filter_passed', type: 'boolean', desc: 'False when a hard rule excluded the job (senior/staff/lead titles for junior candidates, or 5+ years required). Treat false as "do not apply".' },
      { name: 'description_preview', type: 'string', desc: 'First 500 characters of the description.' },
    ],
  },
  { name: 'evaluated', type: 'integer', desc: 'How many jobs were scored before truncating to target_count.' },
  { name: 'returned', type: 'integer', desc: 'Number of candidates actually returned.' },
];

const COMPILE_BODY_FIELDS: FieldDef[] = [
  {
    name: 'resume_json', type: 'object', required: true,
    desc: 'The structured resume to compile. Your agent writes this (tailored per job); the compiler just typesets it.',
    children: [
      { name: 'name / email / phone', type: 'string', required: true, desc: 'Contact header. website, github, and linkedin are optional URL strings rendered as links.' },
      { name: 'experience', type: 'object[]', required: true, desc: 'Each entry: company, location, title, dates, and bullets (string[]). 3–4 bullets per role render best.' },
      { name: 'education', type: 'object[]', required: true, desc: 'Each entry: school, location, degree, dates.' },
      { name: 'skills', type: 'object', required: true, desc: 'Dict of category → comma-separated values, e.g. {"Languages": "Python, Go"}. Not a flat list.' },
      { name: 'projects', type: 'object[]', desc: 'Each entry: name (convention: "Name (Tech1, Tech2)"), dates, bullets (string[]).' },
    ],
  },
  {
    name: 'options', type: 'object',
    desc: 'Typesetting knobs. The defaults produce a dense single page.',
    children: [
      { name: 'font_anchor', type: 'integer', default: '11', desc: 'Starting font size in points. The compiler steps down [10, 9, 8] on overflow and grows up [12, 14] on sparse pages.' },
      { name: 'spacing', type: 'enum', default: '"tight"', desc: <>One of <InlineCode>tight</InlineCode>, <InlineCode>normal</InlineCode>, <InlineCode>relaxed</InlineCode>. With tight, underfilled pages are auto-stretched.</> },
    ],
  },
];

const COMPILE_RESPONSE_FIELDS: FieldDef[] = [
  { name: 'pdf_base64', type: 'string', desc: 'The compiled PDF, base64-encoded. Decode and write to disk.' },
  {
    name: 'diagnostics', type: 'object',
    desc: 'Layout telemetry your agent uses to decide whether to rewrite and recompile.',
    children: [
      { name: 'pages', type: 'integer', desc: 'Page count. The target is always 1.' },
      { name: 'font_size', type: 'integer', desc: 'The font size the ladder locked, e.g. 11.' },
      { name: 'spacing', type: 'string', desc: 'The spacing preset actually used after auto-stretch.' },
      { name: 'fill_ratio', type: 'float (0–1)', desc: 'How much of the page height the content fills. Aim for ≥ 0.85.' },
      { name: 'widows', type: 'object[]', desc: 'Bullets whose last wrapped line is nearly empty. Each entry pinpoints {section, entry, bullet, last_line_chars} — rewrite that bullet (extend with real facts or tighten to one line) and recompile. Empty means the layout is clean.' },
    ],
  },
];

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

const NAV: TocItem[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'authentication', label: 'Authentication' },
  {
    id: 'mcp-for-agents',
    label: 'MCP for Agents',
    children: [
      { id: 'mcp-choose-path', label: 'Choose your path' },
      { id: 'mcp-setup', label: 'Set up your client' },
      { id: 'mcp-workflows', label: 'Workflow examples' },
      { id: 'mcp-local-tex', label: 'Optional local TeX' },
      { id: 'mcp-which-path', label: 'Which path do I need?' },
    ],
  },
  {
    id: 'endpoints',
    label: 'API Reference',
    children: [
      { id: 'ep-jobs', label: 'List jobs' },
      { id: 'ep-job-detail', label: 'Get a job' },
      { id: 'ep-prefilter', label: 'Prefilter & score' },
      { id: 'ep-compile', label: 'Compile resume PDF' },
    ],
  },
  { id: 'errors', label: 'Errors & Rate Limits' },
];

const ALL_NAV_IDS = NAV.flatMap((item) => [item.id, ...(item.children?.map((c) => c.id) ?? [])]);

function topLevelIdFor(activeId: string): string {
  for (const item of NAV) {
    if (item.id === activeId || item.children?.some((c) => c.id === activeId)) return item.id;
  }
  return activeId;
}

const DocsPage: React.FC = () => {
  const [active, setActive] = useState<string>('overview');
  const [lang, setLang] = useState<Lang>('curl');
  const [mcpClient, setMcpClient] = useState<McpClientId>('codex');
  const [mcpMode, setMcpMode] = useState<McpSetupMode>('uvx');
  const resolvedTheme = useResolvedTheme();
  const origin = currentOrigin();
  const mcpSetup = getMcpSetup(mcpClient, mcpMode, '<YOUR_API_KEY_HERE>', origin);
  const selectedMcpClient = getMcpClient(mcpClient);
  const selectedMcpMode = getMcpMode(mcpMode);
  const docsThemeVars = {
    '--lp-bg': resolvedTheme === 'dark' ? '#000000' : '#ffffff',
    '--lp-surface': resolvedTheme === 'dark' ? '#050608' : '#ffffff',
    '--lp-text-primary': resolvedTheme === 'dark' ? '#f8fafc' : '#111827',
    '--lp-text-secondary': resolvedTheme === 'dark' ? '#cbd5e1' : '#374151',
    '--lp-text-tertiary': resolvedTheme === 'dark' ? '#94a3b8' : '#6b7280',
    '--lp-border': resolvedTheme === 'dark' ? 'rgba(255, 255, 255, 0.10)' : 'rgba(17, 24, 39, 0.12)',
  } as React.CSSProperties;

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
    ALL_NAV_IDS.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  return (
    <div className="docs-page min-h-screen bg-bg text-text-primary" style={docsThemeVars}>
      <Header />
      <div className="max-w-[1280px] mx-auto px-6 py-10 lg:flex lg:gap-12">
        {/* Sidebar */}
        <aside className="hidden lg:block w-56 shrink-0">
          <nav className="sticky top-10">
            <div className="font-sans text-[11px] font-semibold uppercase tracking-wide text-text-tertiary mb-3">
              Documentation
            </div>
            <ul className="space-y-0.5 border-l border-lp-border">
              {NAV.map(({ id, label }) => (
                <li key={id}>
                  <a
                    href={`#${id}`}
                    className={`block pl-4 -ml-px py-1.5 font-sans text-[13.5px] border-l transition-colors ${
                      topLevelIdFor(active) === id
                        ? 'border-[var(--docs-accent)] text-[var(--docs-accent)] font-medium'
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
            <nav className="flex flex-wrap gap-2 mt-6 lg:hidden">
              {NAV.map(({ id, label }) => (
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
              <a className="docs-link" href="https://modelcontextprotocol.io" target="_blank" rel="noreferrer">
                Model Context Protocol
              </a>{' '}
              via our open-source{' '}
              <a className="docs-link" href="https://github.com/internship-app1/internship-mcp-server" target="_blank" rel="noreferrer">
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
          </section>

          {/* -------------------------------------------------------- */}
          <section className="mb-14">
            <H2 id="authentication">Authentication</H2>
            <Para>
              Every <InlineCode>/api/v1</InlineCode> request needs a per-user API key in
              the <InlineCode>X-API-Key</InlineCode> header. Generate one on the{' '}
              <Link to="/developer" className="docs-link">
                Developer page
              </Link>{' '}
              — it's shown once, looks like <InlineCode>im_live_…</InlineCode>, and can
              be revoked there at any time. Only a hash is stored on our side.
            </Para>
            <RequestSample
              lang={lang}
              onLangChange={setLang}
              samples={{
                curl: `curl -H "X-API-Key: im_live_..." \\\n  "${API_BASE}/api/v1/jobs?limit=5"`,
                python: `import requests\n\nresp = requests.get(\n    "${API_BASE}/api/v1/jobs",\n    headers={"X-API-Key": "im_live_..."},\n    params={"limit": 5},\n)\nresp.raise_for_status()\nprint(resp.json()["total"], "active jobs")`,
                javascript: `const resp = await fetch(\n  "${API_BASE}/api/v1/jobs?limit=5",\n  { headers: { "X-API-Key": "im_live_..." } }\n);\nif (!resp.ok) throw new Error(\`HTTP \${resp.status}\`);\nconst data = await resp.json();\nconsole.log(data.total, "active jobs");`,
              }}
            />
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
              MCP lets an AI client call Internship Matcher tools directly — no code,
              just a config entry. There are two ways to connect; pick one below.
            </Para>

            <H3 id="mcp-choose-path">Choose your path</H3>
            <div className="grid gap-4 sm:grid-cols-2 mb-6 max-w-[680px]">
              <div className="rounded-lg border border-lp-border p-5">
                <div className="font-sans text-[15px] font-semibold text-text-primary mb-1">
                  Hosted <span className="font-normal text-text-tertiary">(remote MCP)</span>
                </div>
                <p className="font-sans text-[13.5px] leading-6 text-text-secondary mb-3">
                  Job discovery in any chat app. Zero install — nothing runs on your
                  machine.
                </p>
                <ul className="space-y-1.5 font-sans text-[13.5px] leading-6 text-text-secondary list-disc pl-4 mb-3">
                  <li>Works in Claude chat custom connectors and any client that supports remote (Streamable HTTP) MCP</li>
                  <li>Tools: job search, job details, deterministic fit scoring</li>
                  <li>Cannot apply, parse resumes, or touch your local files</li>
                </ul>
                <span className="inline-block rounded-full border border-[var(--docs-accent)]/40 px-2.5 py-1 font-sans text-[12px] text-[var(--docs-accent)]">
                  Best for: trying it out, cloud chats
                </span>
              </div>
              <div className="rounded-lg border border-lp-border p-5">
                <div className="font-sans text-[15px] font-semibold text-text-primary mb-1">
                  Local agent <span className="font-normal text-text-tertiary">(full apply flow)</span>
                </div>
                <p className="font-sans text-[13.5px] leading-6 text-text-secondary mb-3">
                  The complete pipeline, running on your machine.
                </p>
                <ul className="space-y-1.5 font-sans text-[13.5px] leading-6 text-text-secondary list-disc pl-4 mb-3">
                  <li>Resume parsing and your encrypted applicant profile stay local</li>
                  <li>Tailored PDFs, application packets, and an application tracker</li>
                  <li>Prefills forms in your browser via Playwright MCP — you always review and hit submit yourself</li>
                  <li>Needs a client that can launch commands: Claude Code, Codex, Cursor, Windsurf, or Cline</li>
                </ul>
                <span className="inline-block rounded-full border border-[var(--docs-accent)]/40 px-2.5 py-1 font-sans text-[12px] text-[var(--docs-accent)]">
                  Best for: actually applying
                </span>
              </div>
            </div>

            <H3 id="mcp-setup">Set up your client</H3>
            <StepList
              steps={[
                <>
                  Sign in and generate an API key on the{' '}
                  <Link to="/developer" className="docs-link">
                    Developer page
                  </Link>{' '}
                  — it's shown once, so copy it right away.
                </>,
                <>Pick your client and path with the two selectors below.</>,
                <>
                  Copy the generated config into the file shown above the snippet
                  (or run the CLI command, where one is shown), replacing{' '}
                  <InlineCode>&lt;YOUR_API_KEY_HERE&gt;</InlineCode> with your key.
                </>,
                <>Restart your client so it picks up the new MCP server.</>,
                <>Paste the smoke prompt to confirm the tools respond.</>,
              ]}
            />

            <div className="rounded-lg border border-lp-border overflow-hidden mb-6 max-w-[680px]">
              <div className="flex flex-wrap gap-3 p-4 bg-surface border-b border-lp-border">
                <McpSetupDropdown
                  label="Client"
                  value={mcpClient}
                  items={CLIENT_DROPDOWN_ITEMS}
                  onChange={setMcpClient}
                />
                <McpSetupDropdown
                  label="Path"
                  value={mcpMode}
                  items={MODE_DROPDOWN_ITEMS}
                  onChange={setMcpMode}
                />
              </div>

              <div className="p-4 border-b border-lp-border">
                <div className="font-sans text-[13px] font-semibold text-text-primary mb-1">
                  {selectedMcpClient.label} · {selectedMcpMode.label}
                </div>
                <p className="font-sans text-[14px] leading-6 text-text-secondary">
                  {mcpSetup.capability}
                </p>
              </div>

              <CodeSnippet
                title={mcpSetup.configPath}
                code={mcpSetup.snippet}
                language={mcpSetup.snippetLang}
                className="rounded-none border-0 border-b"
              />

              <div className="p-4 border-t border-lp-border bg-bg">
                <div className="font-sans text-[13px] font-semibold text-text-primary mb-2">
                  Smoke prompt — paste this to verify
                </div>
                <pre className="whitespace-pre-wrap font-mono text-[12.5px] leading-relaxed text-text-secondary mb-3">
                  {mcpSetup.smokePrompt}
                </pre>
                <div className="space-y-1 border-t border-lp-border pt-3">
                  {mcpSetup.notes.map((note) => (
                    <p key={note} className="font-sans text-[13px] leading-6 text-text-tertiary">
                      {note}
                    </p>
                  ))}
                  {mcpMode === 'hosted' ? (
                    <p className="font-sans text-[13px] leading-6 text-text-tertiary">
                      In Claude chat, look for "custom connector", "remote MCP", or
                      "Streamable HTTP MCP" and paste the hosted URL. Keep hosted keys
                      disposable and revoke them when done.
                    </p>
                  ) : (
                    <p className="font-sans text-[13px] leading-6 text-text-tertiary">
                      The Playwright entry is a separate, official MCP server the agent
                      uses to prefill application forms in your browser — you always
                      review and hit submit yourself.
                    </p>
                  )}
                </div>
              </div>
            </div>

            <H3 id="mcp-workflows">Workflow examples</H3>
            <Para>
              Once the client can see the MCP tools, the fastest path is to give the
              agent an explicit workflow. These prompts are designed to keep resume data
              local, use deterministic prefiltering first, and ask the agent to inspect
              full job descriptions before making recommendations.
            </Para>
            <div className="grid gap-4 mb-6 max-w-[680px]">
              {AGENT_WORKFLOW_EXAMPLES.map((workflow) => (
                <div key={workflow.id} className="rounded-lg border border-lp-border overflow-hidden">
                  <div className="px-4 py-3 border-b border-lp-border bg-surface">
                    <div className="font-sans text-[14px] font-semibold text-text-primary">
                      {workflow.title}
                    </div>
                    <div className="font-sans text-[13px] text-text-tertiary mt-0.5">
                      {workflow.bestFor}
                    </div>
                  </div>
                  <CodeSnippet
                    title="Agent prompt"
                    code={workflow.prompt}
                    language="plain"
                    wrap
                    className="rounded-none border-0"
                  />
                </div>
              ))}
            </div>

            <H3 id="mcp-local-tex">Optional: local TeX for unlimited compiles</H3>
            <Para>
              The local agent compiles tailored resume PDFs with{' '}
              <InlineCode>pdflatex</InlineCode>. On first run it asks whether to install
              TeX locally (unlimited, fully offline compiles) or fall back to our remote
              compiler, which is capped at 15 compiles/week. If you skip TeX, everything
              else still works.
            </Para>
            <CodeBlock title="Install TeX" lang="bash">{`# macOS
brew install --cask basictex && sudo tlmgr update --self && sudo tlmgr install enumitem titlesec parskip microtype

# Debian / Ubuntu
sudo apt install texlive-latex-extra

# Windows
# Install MiKTeX from https://miktex.org`}</CodeBlock>

            <H3 id="mcp-which-path">Which path do I need?</H3>
            <div className="rounded-lg border border-lp-border divide-y divide-lp-border mb-5 max-w-[680px]">
              {[
                ['Cloud chat that supports remote MCP (e.g. Claude chat)', 'Hosted'],
                ['Coding agent that can run local commands (Claude Code, Codex, Cursor, Windsurf, Cline)', 'Local agent'],
                ['Platform with no MCP support at all', 'Use the REST API below'],
              ].map(([scenario, answer]) => (
                <div key={scenario} className="flex items-center gap-4 px-4 py-3">
                  <span className="flex-1 font-sans text-[14px] leading-6 text-text-secondary">{scenario}</span>
                  <span className="shrink-0 font-sans text-[13px] font-semibold text-[var(--docs-accent)]">{answer}</span>
                </div>
              ))}
            </div>
            <Para>
              Browser-only chats cannot reach files on your laptop or your browser
              session — that always requires the local agent running on your machine.
            </Para>
          </section>

          {/* -------------------------------------------------------- */}
          <section className="mb-14">
            <H2 id="endpoints">API Reference</H2>
            <Para>
              All endpoints live under <InlineCode>/api/v1</InlineCode> and require the{' '}
              <InlineCode>X-API-Key</InlineCode> header. Rate limits are per key. The
              machine-readable contract lives at{' '}
              <a className="docs-link" href="/api/v1/openapi.json" target="_blank" rel="noreferrer">
                /api/v1/openapi.json
              </a>.
            </Para>

            {/* ------------------- GET /jobs ------------------------ */}
            <div id="ep-jobs" className="scroll-mt-24" />
            <Endpoint method="GET" path="/api/v1/jobs" limit="120 / hour">
              <Para>
                List active internship postings, freshest first. The job pool comes from
                continuously scraped sources and is soft-expired after 30 days.
              </Para>
              <RequestSample lang={lang} onLangChange={setLang} samples={JOBS_SAMPLES} />
              <SubLabel>Query parameters</SubLabel>
              <FieldTable fields={JOBS_QUERY_FIELDS} />
              <SubLabel>Response</SubLabel>
              <FieldTable fields={JOBS_RESPONSE_FIELDS} />
              <SubLabel>The Job object</SubLabel>
              <FieldTable fields={JOB_FIELDS} />
            </Endpoint>

            {/* ------------------- GET /jobs/{hash} ----------------- */}
            <div id="ep-job-detail" className="scroll-mt-24" />
            <Endpoint method="GET" path="/api/v1/jobs/{job_hash}" limit="120 / hour">
              <Para>
                One job by its hash. Returns <InlineCode>404</InlineCode> for an unknown
                hash. The response has the same fields as the Job object above, minus{' '}
                <InlineCode>description_preview</InlineCode>, plus:
              </Para>
              <RequestSample lang={lang} onLangChange={setLang} samples={JOB_DETAIL_SAMPLES} />
              <SubLabel>Additional response fields</SubLabel>
              <FieldTable fields={JOB_DETAIL_FIELDS} />
            </Endpoint>

            {/* ------------------- POST /prefilter ------------------ */}
            <div id="ep-prefilter" className="scroll-mt-24" />
            <Endpoint method="POST" path="/api/v1/jobs/prefilter" limit="120 / hour">
              <Para>
                Deterministic scoring of the job pool against a small, PII-free profile.
                The scoring is mechanical — treat it as a prefilter and let your agent
                do the real ranking from the full job descriptions.
              </Para>
              <RequestSample lang={lang} onLangChange={setLang} samples={PREFILTER_SAMPLES} />
              <SubLabel>Request body</SubLabel>
              <FieldTable fields={PREFILTER_BODY_FIELDS} />
              <SubLabel>Response</SubLabel>
              <FieldTable fields={PREFILTER_RESPONSE_FIELDS} />
            </Endpoint>

            {/* ------------------- POST /compile -------------------- */}
            <div id="ep-compile" className="scroll-mt-24" />
            <Endpoint method="POST" path="/api/v1/resume/compile" limit="15 / week · 3 concurrent">
              <Para>
                Fallback PDF compiler for environments without local TeX. The full uvx
                agent uses it only when <InlineCode>pdflatex</InlineCode> is not installed;
                local TeX and Docker compiles never call this endpoint. Over-capacity requests
                are rejected immediately with <InlineCode>429</InlineCode> and a{' '}
                <InlineCode>Retry-After</InlineCode> header rather than queued, and
                identical payloads are served from a content cache.
              </Para>
              <RequestSample lang={lang} onLangChange={setLang} samples={COMPILE_SAMPLES} />
              <SubLabel>Request body</SubLabel>
              <FieldTable fields={COMPILE_BODY_FIELDS} />
              <SubLabel>Response</SubLabel>
              <FieldTable fields={COMPILE_RESPONSE_FIELDS} />
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
                ['429', 'Rate limit exceeded, weekly remote compile quota reached, or all compile slots busy (check Retry-After). Install TeX locally or use Docker to avoid remote compile limits entirely.'],
              ].map(([code, desc]) => (
                <div key={code} className="flex gap-4 px-4 py-3">
                  <code className="font-mono text-[13px] font-semibold text-text-primary w-10 shrink-0">{code}</code>
                  <span className="font-sans text-[14px] leading-6 text-text-secondary">{desc}</span>
                </div>
              ))}
            </div>
            <Para>
              Limits are per API key: jobs and prefilter at 120 requests/hour, remote
              compile at 15/week with 3 concurrent slots. The MCP server surfaces these
              as legible errors to your agent and backs off automatically on network
              failures.
            </Para>
          </section>
        </main>

        <OnThisPage items={NAV} activeId={active} />
      </div>
    </div>
  );
};

export default DocsPage;
