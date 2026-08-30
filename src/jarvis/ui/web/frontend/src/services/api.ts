import {
  ConnectorItem,
  EffortInfo,
  MCPServerItem,
  ModelItem,
  ProviderItem,
  SessionSummary,
  SkillItem,
  SystemHealth,
  ToolDefinition,
  VoiceOption,
} from '../types';

const API_BASE = '/api';

export async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      // fallback to status text
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

// ─── Chat ──────────────────────────────────────────────────────
export const ChatApi = {
  /** Non-streaming fallback used when the WebSocket is unavailable. */
  send: (message: string, session_id?: string) =>
    fetchJson<{ response: string; session_id: string; status: string }>(`${API_BASE}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message, session_id, stream: false }),
    }),
};

// ─── Sessions ──────────────────────────────────────────────────
export const SessionsApi = {
  list: () => fetchJson<SessionSummary[]>(`${API_BASE}/sessions`),
  get: (sessionId: string) =>
    fetchJson<{ session_id: string; messages: any[] }>(`${API_BASE}/sessions/${sessionId}`),
  create: () =>
    fetchJson<{ session_id: string; created_at: string; status: string }>(`${API_BASE}/sessions/new`, {
      method: 'POST',
    }),
  switch: (sessionId: string) =>
    fetchJson<{ status: string; session_id: string }>(`${API_BASE}/sessions/${sessionId}/switch`, {
      method: 'POST',
    }),
  delete: (sessionId: string) =>
    fetchJson<{ status: string; session_id: string }>(`${API_BASE}/sessions/${sessionId}`, {
      method: 'DELETE',
    }),
  rename: (sessionId: string, title: string) =>
    fetchJson<{ status: string; session_id: string; title: string }>(
      `${API_BASE}/sessions/${sessionId}/rename`,
      { method: 'POST', body: JSON.stringify({ title }) }
    ),
};

// ─── Config & Models ───────────────────────────────────────────
export const ConfigApi = {
  get: () => fetchJson<Record<string, any>>(`${API_BASE}/config`),
  update: (configUpdate: Record<string, any>) =>
    fetchJson<{
      status: string;
      message: string;
      rejected: string[];
      /** Set when the patch touched `voice`: whether the subsystem came back up. */
      voice_reloaded?: boolean | null;
      config: Record<string, any>;
    }>(`${API_BASE}/config`, { method: 'PATCH', body: JSON.stringify(configUpdate) }),
  listProviders: () => fetchJson<ProviderItem[]>(`${API_BASE}/config/providers`),
  listModels: (provider?: string) => {
    const url = provider
      ? `${API_BASE}/config/models?provider=${encodeURIComponent(provider)}`
      : `${API_BASE}/config/models`;
    return fetchJson<ModelItem[]>(url);
  },
  switchProvider: (provider: string, model?: string, reasoning_effort?: string) =>
    fetchJson<{ status: string; provider: string; model: string; reasoning_effort?: string }>(
      `${API_BASE}/config/provider/switch`,
      { method: 'POST', body: JSON.stringify({ provider, model, reasoning_effort }) }
    ),
  connectProvider: (
    provider: string,
    keys?: Record<string, string>,
    api_key?: string,
    base_url?: string
  ) =>
    fetchJson<{ status: string; message: string; env_var?: string; env_vars?: string[] }>(
      `${API_BASE}/config/provider/connect`,
      { method: 'POST', body: JSON.stringify({ provider, keys, api_key, base_url }) }
    ),
  getEffort: () => fetchJson<EffortInfo>(`${API_BASE}/config/effort`),
  setEffort: (effort: string) =>
    fetchJson<{ status: string; reasoning_effort: string; model: string; thinking: boolean }>(
      `${API_BASE}/config/effort`,
      { method: 'POST', body: JSON.stringify({ effort }) }
    ),
};

// ─── Skills ────────────────────────────────────────────────────
export const SkillsApi = {
  list: () => fetchJson<SkillItem[]>(`${API_BASE}/skills`),
  get: (name: string) =>
    fetchJson<{ name: string; content: string; enabled: boolean }>(
      `${API_BASE}/skills/${encodeURIComponent(name)}`
    ),
  /** Create a skill from pasted README.md markdown. */
  create: (content: string, name?: string, overwrite = false) =>
    fetchJson<{
      status: string;
      name: string;
      description: string;
      path: string;
      enabled: boolean;
      custom: boolean;
      message: string;
    }>(`${API_BASE}/skills`, {
      method: 'POST',
      body: JSON.stringify({ content, name, overwrite }),
    }),
  remove: (name: string) =>
    fetchJson<{ status: string; name: string }>(`${API_BASE}/skills/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    }),
  directory: () => fetchJson<{ path: string }>(`${API_BASE}/skills/directory`),
  toggle: (name: string, enabled: boolean) =>
    fetchJson<{ status: string; name: string; enabled: boolean }>(
      `${API_BASE}/skills/${encodeURIComponent(name)}/toggle`,
      { method: 'POST', body: JSON.stringify({ enabled }) }
    ),
};

// ─── MCP ───────────────────────────────────────────────────────
export const MCPApi = {
  listServers: () => fetchJson<MCPServerItem[]>(`${API_BASE}/mcp/servers`),
  addServer: (serverData: {
    name: string;
    command: string;
    args: string[];
    env: Record<string, string>;
    transport?: string;
    url?: string;
  }) =>
    fetchJson<{ status: string; name: string; connected: boolean; message: string }>(
      `${API_BASE}/mcp/add`,
      { method: 'POST', body: JSON.stringify(serverData) }
    ),
  toggleServer: (name: string, enabled: boolean) =>
    fetchJson<{
      status: string;
      name: string;
      connected: boolean;
      enabled: boolean;
      message: string;
    }>(`${API_BASE}/mcp/${encodeURIComponent(name)}/toggle`, {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    }),
  deleteServer: (name: string) =>
    fetchJson<{ status: string; name: string }>(`${API_BASE}/mcp/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    }),
  googleOAuth: () =>
    fetchJson<{ status: string; email: string; message: string }>(`${API_BASE}/mcp/auth/google`, {
      method: 'POST',
    }),
};

// ─── Connectors ────────────────────────────────────────────────
export const ConnectorsApi = {
  list: () => fetchJson<ConnectorItem[]>(`${API_BASE}/connectors`),
  configure: (
    name: string,
    data: {
      enabled: boolean;
      bot_token?: string;
      allowed_users?: string[];
      allowed_guilds?: string[];
    }
  ) =>
    fetchJson<{ status: string; name: string; enabled: boolean; message: string }>(
      `${API_BASE}/connectors/${encodeURIComponent(name)}/configure`,
      { method: 'POST', body: JSON.stringify(data) }
    ),
};

// ─── Voice ─────────────────────────────────────────────────────
export const VoiceApi = {
  status: () =>
    fetchJson<{
      enabled: boolean;
      mode: string;
      tts_provider: string;
      stt_provider: string;
      active_voice: string;
    }>(`${API_BASE}/voice/status`),
  /** Lists a provider's catalogue; omit `provider` for the active one. */
  listVoices: (provider?: string) =>
    fetchJson<VoiceOption[]>(
      provider
        ? `${API_BASE}/voice/voices?provider=${encodeURIComponent(provider)}`
        : `${API_BASE}/voice/voices`
    ),
  listProviders: () =>
    fetchJson<{ id: string; active: boolean }[]>(`${API_BASE}/voice/providers`),
  setMode: (mode: string) =>
    fetchJson<{ status: string; mode: string }>(`${API_BASE}/voice/mode`, {
      method: 'POST',
      body: JSON.stringify({ mode }),
    }),
  /** Matches the `{"text": ...}` payload returned by /api/voice/transcribe. */
  transcribe: async (audioBlob: Blob): Promise<{ text: string }> => {
    const formData = new FormData();
    formData.append('file', audioBlob, 'speech.wav');
    const response = await fetch(`${API_BASE}/voice/transcribe`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error('Speech transcription failed');
    const res = await response.json();
    return { text: typeof res?.text === 'string' ? res.text : '' };
  },
  /** `provider` lets Settings preview a provider before the change is saved. */
  synthesize: async (text: string, voice?: string, provider?: string): Promise<Blob> => {
    const response = await fetch(`${API_BASE}/voice/synthesize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice, provider }),
    });
    if (!response.ok) {
      let detail = 'Speech synthesis failed';
      try {
        const err = await response.json();
        detail = err?.detail || err?.message || detail;
      } catch {
        // keep the default message
      }
      throw new Error(detail);
    }
    return response.blob();
  },
};

// ─── Tools & System ────────────────────────────────────────────
export const SystemApi = {
  tools: () => fetchJson<ToolDefinition[]>(`${API_BASE}/tools`),
  health: () => fetchJson<SystemHealth>(`${API_BASE}/system/health`),
  clearMemory: () =>
    fetchJson<{ status: string; message: string }>(`${API_BASE}/system/memory/clear`, {
      method: 'POST',
    }),
};
