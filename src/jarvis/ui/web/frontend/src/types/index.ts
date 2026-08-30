export type MessageRole = 'user' | 'assistant' | 'system' | 'tool';

export type ToolCallStatus = 'running' | 'completed' | 'error';

export interface QuestionItem {
  id?: string;
  question: string;
  options?: string[];
  is_multi_select?: boolean;
  header?: string;
}

export interface AskUserPromptPayload {
  prompt_id: string;
  tool?: string;
  questions: QuestionItem[];
}

export interface ToolCall {
  /** Stable client-side id, so results can be matched back to the right pill. */
  id: string;
  tool: string;
  args: Record<string, any>;
  result?: string;
  /** True when the backend clipped a long result for transport. */
  truncated?: boolean;
  status: ToolCallStatus;
  /** epoch ms */
  startedAt: number;
  durationMs?: number;
  prompt_id?: string;
  questions?: QuestionItem[];
}

export type MessageBlock =
  | { type: 'thought'; id: string; thought: string }
  | { type: 'text'; id: string; content: string }
  | { type: 'tool_call'; id: string; toolCall: ToolCall };

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  thought?: string;
  raw?: string;
  toolCalls?: ToolCall[];
  blocks?: MessageBlock[];
  timestamp: string;
  model?: string;
  isStreaming?: boolean;
  /** Set when the turn ended in an error, so the UI can offer a retry. */
  error?: string;
}

export interface SessionSummary {
  session_id: string;
  title: string;
  message_count: number;
  updated_at: string;
  created_at: string;
  is_active: boolean;
}

/** @deprecated Use {@link SessionSummary}. Retained for older imports. */
export type SessionItem = SessionSummary;

export interface ProviderEnvVarField {
  name: string;
  label: string;
  is_secret: boolean;
  is_set?: boolean;
}

export interface ProviderItem {
  id: string;
  name: string;
  connected: boolean;
  is_active: boolean;
  model_count: number;
  active_model?: string;
  doc_url?: string;
  env_vars?: string[];
  fields?: ProviderEnvVarField[];
}

export interface ModelItem {
  id: string;
  name: string;
  provider: string;
  description?: string;
  context_window?: number;
  max_tokens?: number;
  has_reasoning: boolean;
  available_efforts?: string[];
  is_active: boolean;
}

export interface EffortInfo {
  model: string;
  provider: string;
  supported: boolean;
  available: string[];
  current: string;
}

export interface SkillItem {
  name: string;
  description: string;
  path: string;
  enabled: boolean;
  /** True for skills created by the user — those are the ones we can delete. */
  custom?: boolean;
}

export interface MCPServerItem {
  name: string;
  description: string;
  category: string;
  connected: boolean;
  enabled: boolean;
  tool_count: number;
  requires_oauth: boolean;
  transport?: string;
  custom?: boolean;
}

export interface ConnectorItem {
  name: string;
  status: 'ready' | 'running' | 'disabled' | 'error';
  error?: string | null;
  uptime: number;
  messages_received: number;
  messages_sent: number;
}

export interface ToolDefinition {
  name: string;
  description: string;
  category: string;
  /** Still returned by the API; the UI deliberately does not surface it. */
  dangerous?: boolean;
  parameters: any[];
}

export interface SystemHealth {
  status: string;
  engine_initialized: boolean;
  active_model: string;
  connectors: ConnectorItem[];
  version?: string;
  subsystems?: Record<string, boolean>;
}

export interface VoiceOption {
  id: string;
  name: string;
  gender: string;
  locale: string;
}

// ─── WebSocket protocol ──────────────────────────────────────────
// Mirrors the frames emitted by src/jarvis/api/routes/chat.py.

export type WsEvent =
  | { type: 'start'; session_id: string; model?: string }
  | { type: 'content'; content: string }
  | { type: 'tool_call'; tool: string; args: Record<string, any> }
  | { type: 'tool_result'; tool: string; result: string; truncated?: boolean; status: 'completed' }
  | { type: 'tool_error'; tool: string; result: string; truncated?: boolean; status: 'error' }
  | { type: 'ask_user'; prompt_id: string; tool?: string; questions: QuestionItem[] }
  | { type: 'end'; session_id: string; model?: string }
  | { type: 'error'; message: string }
  | { type: 'pong' };

export type ConnectionState = 'connecting' | 'open' | 'closed';

// ─── Appearance ──────────────────────────────────────────────────

export type BlobStyle = 'hologram' | 'arc_reactor' | 'particle' | 'pulse';
export type UITheme = 'jarvis' | 'obsidian' | 'arc' | 'cyberpunk' | 'matrix' | 'stealth';
export type BackgroundStyle =
  | 'ribbon-field'
  | 'amber-halftone'
  | 'void-field'
  | 'halftone-flow'
  | 'data-pixel'
  | 'dot-matrix'
  | 'constellation'
  | 'crt'
  | 'flow-field'
  | 'classic';

/** Settings panels, in nav order. */
export type SettingsTab =
  | 'model'
  | 'appearance'
  | 'voice'
  | 'memory'
  | 'skills'
  | 'mcp'
  | 'connectors'
  | 'tools'
  | 'about';
