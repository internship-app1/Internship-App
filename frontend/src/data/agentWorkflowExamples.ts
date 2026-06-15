export interface AgentWorkflowExample {
  id: string;
  title: string;
  bestFor: string;
  prompt: string;
}

export const AGENT_WORKFLOW_EXAMPLES: AgentWorkflowExample[] = [
  {
    id: 'fresh-shortlist',
    title: 'Fresh internship shortlist',
    bestFor: 'Finding new roles worth reviewing',
    prompt: `Use Internship Matcher to find software engineering internships posted in the last 72 hours.

Use my resume/profile context from this chat to build a PII-free resume_profile, prefilter the job pool, then inspect the full descriptions for the top candidates.

Return a ranked shortlist of 12 roles with:
- company, title, location, and apply link
- why it fits my background
- the strongest matching skills
- the most important missing skills
- any red flags before I apply`,
  },
  {
    id: 'application-packet',
    title: 'Application packet',
    bestFor: 'Turning one target role into materials',
    prompt: `Use Internship Matcher to fetch the full job description for this job:
<PASTE_JOB_HASH_OR_COMPANY_AND_TITLE>

Then create an application packet for me:
- a concise resume tailoring plan
- 5 resume bullet edits grounded only in my real experience
- a short cover note
- a recruiter outreach message
- likely application questions and truthful draft answers

Do not invent experience. Flag any requirement I cannot honestly claim.`,
  },
  {
    id: 'resume-compile',
    title: 'Tailored resume compile',
    bestFor: 'Producing a one-page PDF from local resume JSON',
    prompt: `Use Internship Matcher to fetch the full job description for this role, tailor my resume JSON to the role, and compile a one-page PDF.

Prefer local pdflatex if available. If local TeX is missing, ask before using the remote compile quota.

After compiling, inspect diagnostics and fix any overflow, underfilled page, or widow lines before giving me the final PDF path.`,
  },
  {
    id: 'daily-watchlist',
    title: 'Daily watchlist',
    bestFor: 'Recurring checks from an agent workspace',
    prompt: `Use Internship Matcher to check for new internships matching this preference profile:
- role types: full-stack, backend, AI application, developer tools
- avoid: mobile-only, defense-clearance, unrelated IT support
- locations: remote, New York, San Francisco, Seattle

Compare against the jobs we already discussed in this workspace. Show only new or meaningfully updated roles and explain why each one should or should not move to my application tracker.`,
  },
];
