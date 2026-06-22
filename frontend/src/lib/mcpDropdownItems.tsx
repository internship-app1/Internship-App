import React from 'react';
import { MCP_CLIENTS, MCP_MODES, McpClientId, McpSetupMode } from '../data/mcpSetup';
import { MCP_CLIENT_ICONS, MCP_MODE_ICONS } from '../components/icons/brand';

export interface McpDropdownEntry<T extends string> {
  id: T;
  label: string;
  group: string;
  icon: React.ReactNode;
}

export const CLIENT_DROPDOWN_ITEMS: McpDropdownEntry<McpClientId>[] = MCP_CLIENTS.map((client) => {
  const Icon = MCP_CLIENT_ICONS[client.id];
  return {
    id: client.id,
    label: client.label,
    group: 'AI agent CLI',
    icon: <Icon className="h-4 w-4" />,
  };
});

export const MODE_DROPDOWN_ITEMS: McpDropdownEntry<McpSetupMode>[] = MCP_MODES.map((mode) => {
  const Icon = MCP_MODE_ICONS[mode.id];
  return {
    id: mode.id,
    label: mode.label,
    group: 'Setup path',
    icon: <Icon className="h-4 w-4" />,
  };
});
