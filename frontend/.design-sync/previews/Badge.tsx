import React from 'react';
import { Badge } from 'frontend';

export const Default = () => <Badge>New</Badge>;
export const Secondary = () => <Badge variant="secondary">In Progress</Badge>;
export const Destructive = () => <Badge variant="destructive">Urgent</Badge>;
export const Outline = () => <Badge variant="outline">Draft</Badge>;
export const AllVariants = () => (
  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', padding: '16px' }}>
    <Badge>Default</Badge>
    <Badge variant="secondary">Secondary</Badge>
    <Badge variant="destructive">Destructive</Badge>
    <Badge variant="outline">Outline</Badge>
  </div>
);
