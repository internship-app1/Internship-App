export interface AgentWorkflowExample {
  id: string;
  title: string;
  bestFor: string;
  prompt: string;
}

export const AGENT_WORKFLOW_EXAMPLES: AgentWorkflowExample[] = [
  {
    id: 'find-and-apply',
    title: 'Find and apply',
    bestFor: 'The full loop in one prompt',
    prompt: `Use the Internship Matcher MCP to find me the most relevant and recent jobs based on my resume. Then apply to the top 3.`,
  },
  {
    id: 'fresh-shortlist',
    title: 'Find me internships',
    bestFor: 'Browse what\'s out there right now',
    prompt: `Use the Internship Matcher MCP to find me the most relevant internships based on my resume. Show me the top 10 with why each one fits.`,
  },
  {
    id: 'application-packet',
    title: 'Tailor my resume for a job',
    bestFor: 'One job, ready-to-send materials',
    prompt: `Use Internship Matcher to fetch the full description for this job: <PASTE_JOB_LINK_OR_COMPANY_AND_TITLE>. Then tailor my resume for it and compile a PDF.`,
  },
  {
    id: 'daily-watchlist',
    title: 'What\'s new today',
    bestFor: 'Quick daily check',
    prompt: `Use Internship Matcher to check for any new internships posted today that match my profile. Only show me ones I haven't seen before.`,
  },
];
