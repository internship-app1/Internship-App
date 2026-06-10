export type McpClientId = 'claude-code' | 'codex' | 'cursor' | 'windsurf' | 'cline';
export type McpSetupMode = 'hosted' | 'uvx' | 'docker';

export interface McpClient {
  id: McpClientId;
  label: string;
  configPath: string;
}

export interface McpMode {
  id: McpSetupMode;
  label: string;
  shortLabel: string;
}

export interface McpSetup {
  title: string;
  configPath: string;
  snippet: string;
  capability: string;
  setupSteps: string[];
  notes: string[];
  smokePrompt: string;
}

export const MCP_CLIENTS: McpClient[] = [
  { id: 'claude-code', label: 'Claude Code', configPath: '.mcp.json (project root)' },
  { id: 'codex', label: 'Codex', configPath: '~/.codex/config.toml' },
  { id: 'cursor', label: 'Cursor', configPath: '~/.cursor/mcp.json' },
  { id: 'windsurf', label: 'Windsurf', configPath: '~/.codeium/windsurf/mcp_config.json' },
  { id: 'cline', label: 'Cline', configPath: 'cline_mcp_settings.json' },
];

export const MCP_MODES: McpMode[] = [
  { id: 'hosted', label: 'Hosted discovery', shortLabel: 'Hosted' },
  { id: 'uvx', label: 'Full agent via uvx', shortLabel: 'uvx' },
  { id: 'docker', label: 'Docker advanced', shortLabel: 'Docker' },
];

const HOSTED_SMOKE_PROMPT = 'Use Internship Matcher to list software internships posted in the last 3 days. Then score which ones fit a student with Python, React, and backend API experience.';

const FULL_AGENT_SMOKE_PROMPT = 'Set up my internship applicant profile. Then parse my resume at /absolute/path/to/resume.pdf, extract my skills, find postings from the last 3 days that fit me, tailor my resume for the best match, build the application packet, and prefill the form for my review. Stop before submitting anything.';

function mcpJson(command: string, args: string[], apiKey: string): string {
  return JSON.stringify(
    {
      mcpServers: {
        internship: {
          command,
          args,
          env: { INTERNSHIP_API_KEY: apiKey },
        },
        playwright: { command: 'npx', args: ['@playwright/mcp@latest'] },
      },
    },
    null,
    2,
  );
}

function hostedJson(url: string): string {
  return JSON.stringify(
    {
      mcpServers: {
        internship: { url },
      },
    },
    null,
    2,
  );
}

function codexToml(mode: McpSetupMode, apiKey: string): string {
  const command = mode === 'docker' ? 'docker' : 'uvx';
  const args = mode === 'docker'
    ? '["run", "-i", "--rm", "-v", "internship-home:/root/.internship-agent", "-e", "INTERNSHIP_API_KEY", "ghcr.io/internship-app1/internship-mcp-server:latest"]'
    : '["internship-mcp"]';

  return [
    '# Save this in ~/.codex/config.toml',
    '[mcp_servers.internship]',
    `command = "${command}"`,
    `args = ${args}`,
    `env = { INTERNSHIP_API_KEY = "${apiKey}" }`,
    '',
    '[mcp_servers.playwright]',
    'command = "npx"',
    'args = ["@playwright/mcp@latest"]',
    '',
    '# CLI alternative:',
    mode === 'docker'
      ? `# codex mcp add internship --env INTERNSHIP_API_KEY=${apiKey} -- docker run -i --rm -v internship-home:/root/.internship-agent -e INTERNSHIP_API_KEY ghcr.io/internship-app1/internship-mcp-server:latest`
      : `# codex mcp add internship --env INTERNSHIP_API_KEY=${apiKey} -- uvx internship-mcp`,
    '# codex mcp add playwright -- npx @playwright/mcp@latest',
  ].join('\n');
}

function dockerJson(apiKey: string): string {
  return mcpJson(
    'docker',
    [
      'run',
      '-i',
      '--rm',
      '-v',
      'internship-home:/root/.internship-agent',
      '-e',
      'INTERNSHIP_API_KEY',
      'ghcr.io/internship-app1/internship-mcp-server:latest',
    ],
    apiKey,
  );
}

function hostedSnippet(client: McpClientId, url: string): string {
  if (client === 'codex') {
    return `codex mcp add internship --url "${url}"`;
  }
  if (client === 'claude-code') {
    return `claude mcp add -t http internship "${url}"`;
  }
  return hostedJson(url);
}

export function getMcpClient(clientId: McpClientId): McpClient {
  return MCP_CLIENTS.find((client) => client.id === clientId) ?? MCP_CLIENTS[0];
}

export function getMcpMode(modeId: McpSetupMode): McpMode {
  return MCP_MODES.find((mode) => mode.id === modeId) ?? MCP_MODES[1];
}

export function getMcpSetup(clientId: McpClientId, mode: McpSetupMode, apiKey: string, origin: string): McpSetup {
  const client = getMcpClient(clientId);
  const displayKey = apiKey || '<YOUR_API_KEY_HERE>';
  const hostedUrl = `${origin}/mcp?key=${displayKey}`;

  if (mode === 'hosted') {
    return {
      title: `${client.label} hosted discovery`,
      configPath: client.id === 'codex' || client.id === 'claude-code'
        ? 'Run this CLI command'
        : client.configPath,
      snippet: hostedSnippet(client.id, hostedUrl),
      capability: 'Hosted MCP is zero-install and exposes job search, job details, and deterministic fit scoring. Applying, resume/profile work, browser prefill, and local files require the full local agent.',
      setupSteps: [
        'Choose your client.',
        'Choose hosted discovery.',
        'Copy this config or command.',
        'Restart or reload your agent.',
        'Run the smoke prompt.',
      ],
      notes: [
        `Hosted HTTP MCP URL: ${hostedUrl}`,
        'Hosted mode is the right path for Claude chat custom connectors and other cloud chats that support remote Streamable HTTP MCP.',
      ],
      smokePrompt: HOSTED_SMOKE_PROMPT,
    };
  }

  const fullAgentCapability = mode === 'uvx'
    ? 'Full uvx mode runs the Internship Matcher MCP server locally with Playwright MCP. Resume parsing, encrypted profile storage, application packets, browser prefill, and local compile support run on your machine.'
    : 'Docker mode is the advanced reproducible path. It runs the local agent from a container while still pairing it with Playwright MCP for browser prefill.';

  const snippet = client.id === 'codex'
    ? codexToml(mode, displayKey)
    : mode === 'docker'
      ? dockerJson(displayKey)
      : mcpJson('uvx', ['internship-mcp'], displayKey);

  return {
    title: `${client.label} ${mode === 'uvx' ? 'full local agent' : 'Docker advanced'}`,
    configPath: client.configPath,
    snippet,
    capability: fullAgentCapability,
    setupSteps: [
      'Choose your client.',
      mode === 'uvx' ? 'Choose full local agent via uvx.' : 'Choose Docker advanced.',
      'Copy this config.',
      'Restart your agent.',
      'Run the smoke prompt.',
    ],
    notes: client.id === 'codex'
      ? [
          'Codex reads MCP servers from ~/.codex/config.toml or from codex mcp add.',
          '.mcp.json is not the primary Codex path; keep it for Claude Code, Cursor, Windsurf, or Cline.',
        ]
      : [
          `Save this in ${client.configPath}.`,
          'The Playwright MCP is included so the local agent can prefill forms in your browser for review.',
        ],
    smokePrompt: FULL_AGENT_SMOKE_PROMPT,
  };
}
