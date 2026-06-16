export interface User {
  name?: string;
  email: string;
  provider: string;
}

export interface AIReasoning {
  score: number;
  resume_complexity: string;
  complexity_score: number;
  experience_match: string;
  skill_match_count: number;
  reasoning: string;
  red_flags: string[];
  skill_matches: string[];
  skill_gaps: string[];
}

export interface Job {
  title: string;
  company: string;
  location: string;
  job_hash?: string;
  description?: string;
  score?: number;
  match_score?: number;
  match_description: string;
  ai_reasoning?: AIReasoning;
  apply_link?: string;
  requirements?: string[];
  required_skills?: string[];
  url?: string;
  first_seen?: string;
  last_seen?: string;
}

export type SavedJobStatus = 'saved' | 'interested' | 'applied' | 'interviewing' | 'rejected' | 'offer' | 'ghosted';

export interface SavedJob {
  id: number;
  job_hash: string;
  status: SavedJobStatus;
  notes: string;
  deadline?: string | null;
  applied_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  job?: Job | null;
}

export interface MatchResults {
  jobs: Job[];
  error?: string;
}
