import React from 'react';
import { JobCard } from 'frontend';

const sampleJob = {
  title: 'Software Engineer Intern',
  company: 'Stripe',
  location: 'San Francisco, CA',
  job_hash: 'demo-hash-001',
  description: 'Join our payments infrastructure team to build reliable, scalable systems used by millions of businesses. Work with senior engineers on real production code.',
  score: 92,
  match_score: 92,
  match_description: 'Strong match — your Python and distributed systems experience aligns well with this role.',
  ai_reasoning: {
    score: 92,
    resume_complexity: 'medium',
    complexity_score: 75,
    experience_match: 'strong',
    skill_match_count: 8,
    reasoning: 'Candidate has strong backend experience with Python and distributed systems, matching core requirements. Previous internship at a fintech company is a strong signal.',
    red_flags: [],
    skill_matches: ['Python', 'REST APIs', 'Distributed Systems', 'SQL', 'Git'],
    skill_gaps: ['Go', 'Kubernetes'],
  },
  apply_link: 'https://stripe.com/jobs',
  required_skills: ['Python', 'Go', 'Distributed Systems', 'SQL'],
  first_seen: new Date(Date.now() - 2 * 86400000).toISOString(),
};

const lowMatchJob = {
  title: 'ML Research Intern',
  company: 'DeepMind',
  location: 'London, UK',
  job_hash: 'demo-hash-002',
  description: 'Research internship focused on reinforcement learning and large-scale model training.',
  score: 54,
  match_score: 54,
  match_description: 'Partial match — strong CS fundamentals but limited ML/research experience.',
  match_description: 'Partial match — strong CS fundamentals but limited ML experience.',
  ai_reasoning: {
    score: 54,
    resume_complexity: 'medium',
    complexity_score: 70,
    experience_match: 'partial',
    skill_match_count: 3,
    reasoning: 'Candidate has solid CS foundations but lacks the research background and ML specialization this role requires.',
    red_flags: ['No published research', 'Limited ML coursework'],
    skill_matches: ['Python', 'Linear Algebra', 'Git'],
    skill_gaps: ['PyTorch', 'Reinforcement Learning', 'Academic Research'],
  },
  apply_link: 'https://deepmind.google/careers',
  required_skills: ['Python', 'PyTorch', 'Machine Learning', 'Research'],
  first_seen: new Date(Date.now() - 5 * 86400000).toISOString(),
};

export const HighMatch = () => (
  <div style={{ width: '680px', padding: '16px' }}>
    <JobCard job={sampleJob} />
  </div>
);

export const LowMatch = () => (
  <div style={{ width: '680px', padding: '16px' }}>
    <JobCard job={lowMatchJob} />
  </div>
);

export const Saved = () => (
  <div style={{ width: '680px', padding: '16px' }}>
    <JobCard job={sampleJob} isSaved={true} />
  </div>
);
