import React from 'react';
import { Progress } from 'frontend';

export const Low = () => (
  <div style={{ width: '280px', padding: '16px' }}>
    <p style={{ fontSize: '13px', marginBottom: '8px', color: 'hsl(var(--muted-foreground))' }}>Analyzing resume… 25%</p>
    <Progress value={25} />
  </div>
);

export const Mid = () => (
  <div style={{ width: '280px', padding: '16px' }}>
    <p style={{ fontSize: '13px', marginBottom: '8px', color: 'hsl(var(--muted-foreground))' }}>Matching jobs… 60%</p>
    <Progress value={60} />
  </div>
);

export const Complete = () => (
  <div style={{ width: '280px', padding: '16px' }}>
    <p style={{ fontSize: '13px', marginBottom: '8px', color: 'hsl(var(--muted-foreground))' }}>Done! 100%</p>
    <Progress value={100} />
  </div>
);
