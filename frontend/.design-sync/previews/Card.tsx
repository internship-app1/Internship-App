import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, Button, Badge } from 'frontend';

export const Simple = () => (
  <Card style={{ width: '320px', margin: '16px' }}>
    <CardHeader>
      <CardTitle>Software Engineer Intern</CardTitle>
      <CardDescription>Stripe · San Francisco, CA</CardDescription>
    </CardHeader>
    <CardContent>
      <p style={{ fontSize: '14px', color: 'hsl(var(--muted-foreground))' }}>
        Work on payment infrastructure used by millions of businesses worldwide.
      </p>
    </CardContent>
  </Card>
);

export const WithFooter = () => (
  <Card style={{ width: '320px', margin: '16px' }}>
    <CardHeader>
      <CardTitle>Frontend Developer Intern</CardTitle>
      <CardDescription>Vercel · Remote</CardDescription>
    </CardHeader>
    <CardContent>
      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
        <Badge variant="secondary">React</Badge>
        <Badge variant="secondary">TypeScript</Badge>
        <Badge variant="secondary">Next.js</Badge>
      </div>
    </CardContent>
    <CardFooter>
      <Button size="sm">Apply Now</Button>
    </CardFooter>
  </Card>
);

export const Minimal = () => (
  <Card style={{ width: '280px', margin: '16px', padding: '16px' }}>
    <CardTitle style={{ fontSize: '16px', marginBottom: '8px' }}>Quick Note</CardTitle>
    <p style={{ fontSize: '14px', color: 'hsl(var(--muted-foreground))' }}>
      A simple card with minimal content.
    </p>
  </Card>
);
