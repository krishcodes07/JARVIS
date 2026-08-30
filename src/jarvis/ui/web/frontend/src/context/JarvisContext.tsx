import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { audioService } from '../services/audio';
import { ChatApi, ConfigApi, SessionsApi, VoiceApi } from '../services/api';
import { jarvisSocket } from '../services/websocket';
import { ChatMessage, ConnectionState, MessageBlock, SessionSummary, ToolCall, WsEvent } from '../types';
import { parseThinkTags, stripMarkdownForSpeech } from '../utils/thinkParser';

type FrequencyListener = (data: Uint8Array) => void;

/** Where a hands-free voice session currently is in its listen → send → reply loop. */
export type VoiceStatus = 'idle' | 'listening' | 'transcribing' | 'thinking' | 'speaking';

interface JarvisContextType {
  // Chat
  messages: ChatMessage[];
  isGenerating: boolean;
  connectionState: ConnectionState;
  activeModel: string;
  activeProvider: string;
  reasoningEffort: string;
  userName: string;
  sendMessage: (text: string) => Promise<void>;
  stopGeneration: () => void;
  regenerate: () => Promise<void>;
  editAndResend: (messageId: string, newText: string) => Promise<void>;
  clearActiveChat: () => void;
  updateActiveModel: (provider: string, model: string, effort?: string) => Promise<void>;
  setReasoningEffort: (effort: string) => Promise<void>;
  setUserName: (name: string) => void;
  reconnect: () => void;
  respondToAskUser: (promptId: string, response: any) => void;

  // Sessions
  sessions: SessionSummary[];
  currentSessionId: string;
  isDrawerOpen: boolean;
  setDrawerOpen: (open: boolean) => void;
  toggleDrawer: () => void;
  selectSession: (sessionId: string) => Promise<void>;
  createNewSession: () => Promise<string>;
  deleteSession: (sessionId: string) => Promise<void>;
  renameSession: (sessionId: string, newTitle: string) => Promise<void>;
  loadSessions: () => Promise<void>;

  // Voice
  /** True while the microphone is actually capturing — drives orb reactivity. */
  isVoiceMode: boolean;
  /** True while transcription is in progress after recording stops. */
  voiceTranscribing: boolean;
  /** True when the inline voice chat UI is active (blob centered, auto-send loop). */
  isVoiceChatActive: boolean;
  /** True for the whole hands-free session, including while JARVIS is replying. */
  isVoiceSession: boolean;
  voiceStatus: VoiceStatus;
  voiceError: string;
  liveVoiceTranscript: string;
  /** Last user message in voice chat (for inline display). */
  voiceChatUserMsg: string;
  /** Last AI response in voice chat (for inline display). */
  voiceChatAiMsg: string;
  /** Name of the tool Jarvis is currently using in voice mode. */
  voiceToolName: string;
  /** Enter inline voice chat mode — blob goes center, auto-send loop starts. */
  startVoiceChat: () => Promise<void>;
  /** Leave inline voice chat mode. */
  endVoiceChat: () => void;
  /** Stop TTS playback without leaving voice mode — resumes listening. */
  stopTts: () => void;
  /** Legacy: Enter hands-free mode on the current session and start listening. */
  startVoiceSession: () => Promise<void>;
  /** Legacy: Leave hands-free mode, dropping any half-captured utterance. */
  endVoiceSession: () => void;
  /**
   * Subscribe to microphone spectrum frames. Levels are pushed straight to
   * subscribers instead of through React state — at ~60 fps, state updates would
   * re-render the whole tree and re-initialise the orb canvas every frame.
   */
  subscribeToAudioLevels: (listener: FrequencyListener) => () => void;
  getAudioLevels: () => Uint8Array;
}

const JarvisContext = createContext<JarvisContextType | undefined>(undefined);

const EMPTY_LEVELS = new Uint8Array(32);

const nowLabel = () =>
  new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

let toolSeq = 0;
const nextToolId = () => `tool-${Date.now()}-${++toolSeq}`;

export const JarvisProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting');
  const [activeModel, setActiveModel] = useState<string>('');
  const [activeProvider, setActiveProvider] = useState<string>('openai');
  const [reasoningEffort, setReasoningEffortState] = useState<string>('none');
  const [userName, setUserNameState] = useState<string>('Sir');

  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [isDrawerOpen, setDrawerOpen] = useState<boolean>(false);

  // Voice
  const [isVoiceMode, setIsVoiceMode] = useState<boolean>(false);
  const [voiceTranscribing, setVoiceTranscribing] = useState<boolean>(false);
  const [isVoiceSession, setIsVoiceSession] = useState<boolean>(false);
  const [isVoiceChatActive, setIsVoiceChatActive] = useState<boolean>(false);
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>('idle');
  const [voiceError, setVoiceError] = useState<string>('');
  const [liveVoiceTranscript, setLiveVoiceTranscript] = useState<string>('');
  const [voiceChatUserMsg, setVoiceChatUserMsg] = useState<string>('');
  const [voiceChatAiMsg, setVoiceChatAiMsg] = useState<string>('');
  const [voiceToolName, setVoiceToolName] = useState<string>('');

  // The voice loop runs from callbacks (a VAD frame, a socket frame) that outlive
  // the render they were created in, so its state lives in refs as well.
  const voiceSessionRef = useRef<boolean>(false);
  const voiceChatRef = useRef<boolean>(false);
  const liveTranscriptRef = useRef<string>('');
  const awaitingReplyRef = useRef<boolean>(false);
  const beginListeningRef = useRef<() => Promise<void>>(async () => {});
  const finaliseUtteranceRef = useRef<() => Promise<void>>(async () => {});
  const sendMessageRef = useRef<(text: string) => Promise<void>>(async () => {});

  // Audio levels live outside React so the orb can read them per-frame.
  const audioLevelsRef = useRef<Uint8Array>(EMPTY_LEVELS);
  const levelListenersRef = useRef<Set<FrequencyListener>>(new Set());
  const stepRawRef = useRef<string>('');
  const ttsSentIndexRef = useRef<number>(0);
  const ttsQueueRef = useRef<Promise<void>>(Promise.resolve());
  const ttsAbortedRef = useRef<boolean>(false);

  // Latest session id for callbacks that must not re-subscribe on every change.
  const sessionIdRef = useRef<string>(currentSessionId);
  useEffect(() => {
    sessionIdRef.current = currentSessionId;
  }, [currentSessionId]);

  const lastPromptRef = useRef<string>('');

  // ─── Audio level fan-out ──────────────────────────────────────
  const subscribeToAudioLevels = useCallback((listener: FrequencyListener) => {
    levelListenersRef.current.add(listener);
    return () => {
      levelListenersRef.current.delete(listener);
    };
  }, []);

  const getAudioLevels = useCallback(() => audioLevelsRef.current, []);

  const publishAudioLevels = useCallback((data: Uint8Array) => {
    audioLevelsRef.current = data;
    levelListenersRef.current.forEach((fn) => fn(data));
  }, []);

  // ─── Config ───────────────────────────────────────────────────
  const loadInitialConfig = useCallback(async () => {
    try {
      const cfg = await ConfigApi.get();
      if (cfg?.provider?.model) setActiveModel(cfg.provider.model);
      if (cfg?.provider?.active) setActiveProvider(cfg.provider.active);
      if (cfg?.provider?.reasoning_effort) setReasoningEffortState(cfg.provider.reasoning_effort);

      const name = cfg?.user_name || cfg?.jarvis?.user_name || cfg?.jarvis?.user;
      if (name) setUserNameState(name);
    } catch (e) {
      console.warn('Could not load initial config:', e);
    }
  }, []);

  const setUserName = useCallback((name: string) => {
    setUserNameState(name);
    ConfigApi.update({ jarvis: { user_name: name } }).catch((e) =>
      console.warn('Failed to persist user name:', e)
    );
  }, []);

function formatTimestamp(ts?: string): string {
  if (!ts) return nowLabel();
  try {
    const d = new Date(ts);
    if (!isNaN(d.getTime())) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
  } catch {}
  return ts;
}

function reconstructSessionMessages(rawMessages: any[], sid: string): ChatMessage[] {
  const result: ChatMessage[] = [];
  let currentAssistant: ChatMessage | null = null;

  // Pre-index tool messages by tool_call_id and tool_name for quick lookup
  const toolResults = new Map<string, any>();
  for (const m of rawMessages) {
    if (m.role === 'tool') {
      if (m.tool_call_id) toolResults.set(m.tool_call_id, m);
      if (m.tool_name) toolResults.set(`name:${m.tool_name}`, m);
      if (m.name) toolResults.set(`name:${m.name}`, m);
    }
  }

  for (let i = 0; i < rawMessages.length; i++) {
    const m = rawMessages[i];

    if (m.role === 'user') {
      currentAssistant = null;
      result.push({
        id: `${sid}-user-${i}`,
        role: 'user',
        content: m.content || '',
        timestamp: formatTimestamp(m.timestamp),
      });
      continue;
    }

    if (m.role === 'system') {
      currentAssistant = null;
      result.push({
        id: `${sid}-system-${i}`,
        role: 'system',
        content: m.content || '',
        timestamp: formatTimestamp(m.timestamp),
      });
      continue;
    }

    if (m.role === 'tool') {
      // Attached to assistant tool_calls; omit raw unformatted message
      continue;
    }

    if (m.role === 'assistant') {
      const parsed = parseThinkTags(m.content || '', m.thought);

      // Parse tool calls if present
      const toolCalls: ToolCall[] = [];
      const rawToolCalls = Array.isArray(m.tool_calls) ? m.tool_calls : [];
      for (const tc of rawToolCalls) {
        const tcId = tc.id || tc.tool_call_id || nextToolId();
        const toolName = tc.function?.name || tc.name || tc.tool || 'tool';
        let toolArgs: Record<string, any> = {};
        try {
          if (tc.function?.arguments) {
            toolArgs =
              typeof tc.function.arguments === 'string'
                ? JSON.parse(tc.function.arguments)
                : tc.function.arguments;
          } else if (tc.args) {
            toolArgs = tc.args;
          }
        } catch {
          toolArgs = {};
        }

        const toolMsg = toolResults.get(tcId) || toolResults.get(`name:${toolName}`);
        const resultText = toolMsg
          ? typeof toolMsg.content === 'string'
            ? toolMsg.content
            : JSON.stringify(toolMsg.content)
          : undefined;
        const isError = resultText?.toLowerCase().startsWith('error') || false;

        toolCalls.push({
          id: tcId,
          tool: toolName,
          args: toolArgs,
          result: resultText,
          status: toolMsg ? (isError ? 'error' : 'completed') : 'completed',
          startedAt: 0,
        });
      }

      // Build blocks for this assistant message in chronological order
      const blocks: MessageBlock[] = [];
      if (parsed.thought) {
        blocks.push({
          type: 'thought',
          id: `${sid}-th-${i}`,
          thought: parsed.thought,
        });
      }
      if (parsed.content) {
        blocks.push({
          type: 'text',
          id: `${sid}-tx-${i}`,
          content: parsed.content,
        });
      }
      for (const tc of toolCalls) {
        blocks.push({
          type: 'tool_call',
          id: `${sid}-tc-${tc.id}`,
          toolCall: tc,
        });
      }

      // If currentAssistant exists for this user turn, append subsequent steps to it
      if (currentAssistant) {
        currentAssistant.blocks = [...(currentAssistant.blocks || []), ...blocks];
        currentAssistant.toolCalls = [...(currentAssistant.toolCalls || []), ...toolCalls];
        if (parsed.content) {
          currentAssistant.content = currentAssistant.content
            ? `${currentAssistant.content}\n\n${parsed.content}`
            : parsed.content;
        }
        if (parsed.thought) {
          currentAssistant.thought = currentAssistant.thought
            ? `${currentAssistant.thought}\n\n${parsed.thought}`
            : parsed.thought;
        }
      } else {
        currentAssistant = {
          id: `${sid}-assistant-${i}`,
          role: 'assistant',
          content: parsed.content || '',
          thought: parsed.thought,
          toolCalls,
          blocks,
          timestamp: formatTimestamp(m.timestamp),
          model: m.model,
        };
        result.push(currentAssistant);
      }
    }
  }

  return result;
}

  // ─── Sessions ─────────────────────────────────────────────────
  const loadSessionMessages = useCallback(async (sid: string) => {
    try {
      const res = await SessionsApi.get(sid);
      const formatted = reconstructSessionMessages(res.messages || [], sid);
      setMessages(formatted);
    } catch {
      setMessages([]);
    }
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      const list = await SessionsApi.list();
      setSessions(list);
      const sid = sessionIdRef.current;
      if (sid) {
        const found = list.find((s) => s.session_id === sid);
        if (found) {
          await loadSessionMessages(sid);
        }
      }
    } catch (e) {
      console.warn('Could not load sessions:', e);
    }
  }, [loadSessionMessages]);

  const selectSession = useCallback(
    async (sid: string) => {
      setCurrentSessionId(sid);
      sessionIdRef.current = sid;
      try {
        await SessionsApi.switch(sid);
      } catch (e) {
        console.warn('Could not switch session:', e);
      }
      await loadSessionMessages(sid);
      setDrawerOpen(false);
    },
    [loadSessionMessages]
  );

  const createNewSession = useCallback(async (): Promise<string> => {
    const res = await SessionsApi.create();
    setCurrentSessionId(res.session_id);
    sessionIdRef.current = res.session_id;
    setMessages([]);
    await loadSessions();
    setDrawerOpen(false);
    return res.session_id;
  }, [loadSessions]);

  const clearActiveChat = useCallback(() => {
    setCurrentSessionId('');
    sessionIdRef.current = '';
    setMessages([]);
  }, []);

  const deleteSession = useCallback(
    async (sid: string) => {
      await SessionsApi.delete(sid);
      if (sid === sessionIdRef.current) {
        clearActiveChat();
      }
      await loadSessions();
    },
    [clearActiveChat, loadSessions]
  );

  const renameSession = useCallback(
    async (sid: string, newTitle: string) => {
      // Optimistic: the sidecar write is cheap but the list refetch is not.
      setSessions((prev) =>
        prev.map((s) => (s.session_id === sid ? { ...s, title: newTitle } : s))
      );
      try {
        await SessionsApi.rename(sid, newTitle);
      } finally {
        await loadSessions();
      }
    },
    [loadSessions]
  );

  const updateActiveModel = useCallback(
    async (provider: string, model: string, effort?: string) => {
      const res = await ConfigApi.switchProvider(provider, model, effort);
      setActiveProvider(res.provider);
      setActiveModel(res.model);
      if (res.reasoning_effort) setReasoningEffortState(res.reasoning_effort);
    },
    []
  );

  const setReasoningEffort = useCallback(async (effort: string) => {
    const res = await ConfigApi.setEffort(effort);
    setReasoningEffortState(res.reasoning_effort);
  }, []);

  const toggleDrawer = useCallback(() => setDrawerOpen((prev) => !prev), []);

  const queueSentenceTts = useCallback((sentenceText: string) => {
    if (!voiceChatRef.current || ttsAbortedRef.current) return;
    const clean = stripMarkdownForSpeech(sentenceText).trim();
    if (!clean) return;

    // Immediately trigger backend synthesis in parallel
    const synthPromise = VoiceApi.synthesize(clean).catch((err) => {
      console.warn('Sentence synthesis failed, will fall back if needed:', err);
      return null;
    });

    // Queue playback sequentially
    ttsQueueRef.current = ttsQueueRef.current.then(async () => {
      if (!voiceChatRef.current || ttsAbortedRef.current) return;
      const audioBlob = await synthPromise;
      if (!voiceChatRef.current || ttsAbortedRef.current) return;

      setVoiceStatus('speaking');

      if (audioBlob && audioBlob.size > 0) {
        try {
          await audioService.playAudio(audioBlob);
        } catch (e) {
          console.warn('Sentence audio playback failed:', e);
        }
      } else if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        await new Promise<void>((resolve) => {
          const utterance = new SpeechSynthesisUtterance(clean);
          utterance.onend = () => resolve();
          utterance.onerror = () => resolve();
          window.speechSynthesis.speak(utterance);
        });
      }
    });
  }, []);

  // ─── WebSocket lifecycle ──────────────────────────────────────
  useEffect(() => {
    void loadInitialConfig();
    void loadSessions();
    // Ref-counted, so StrictMode's double mount/unmount can't kill reconnect.
    const release = jarvisSocket.acquire();
    const unsubState = jarvisSocket.onStateChange(setConnectionState);
    return () => {
      unsubState();
      release();
    };
  }, [loadInitialConfig, loadSessions]);

  const reconnect = useCallback(() => jarvisSocket.reconnectNow(), []);

  // ─── Message mutation helpers ─────────────────────────────────

  /** Apply a patch to the trailing assistant message, if there is one. */
  const patchLastAssistant = useCallback(
    (patch: (msg: ChatMessage) => ChatMessage) => {
      setMessages((prev) => {
        for (let i = prev.length - 1; i >= 0; i--) {
          if (prev[i].role === 'assistant') {
            const copy = [...prev];
            copy[i] = patch({ ...prev[i] });
            return copy;
          }
        }
        return prev;
      });
    },
    []
  );

  /** Resolve the oldest still-running pill for a tool name. */
  const resolveToolCall = useCallback(
    (tool: string, result: string, truncated: boolean, status: 'completed' | 'error') => {
      patchLastAssistant((msg) => {
        const calls = msg.toolCalls ? [...msg.toolCalls] : [];
        const idx = calls.findIndex((c) => c.tool === tool && c.status === 'running');
        if (idx === -1) {
          // A result with no matching pill (e.g. after a reload) still deserves
          // to be shown rather than dropped.
          const newTool: ToolCall = {
            id: nextToolId(),
            tool,
            args: {},
            result,
            truncated,
            status,
            startedAt: Date.now(),
            durationMs: 0,
          };
          calls.push(newTool);
          msg.blocks = [...(msg.blocks || []), { type: 'tool_call', id: newTool.id, toolCall: newTool }];
        } else {
          calls[idx] = {
            ...calls[idx],
            result,
            truncated,
            status,
            durationMs: Date.now() - calls[idx].startedAt,
          };
          if (msg.blocks) {
            msg.blocks = msg.blocks.map((b) =>
              b.type === 'tool_call' && b.toolCall.id === calls[idx].id
                ? { ...b, toolCall: calls[idx] }
                : b
            );
          }
        }
        msg.toolCalls = calls;
        return msg;
      });
    },
    [patchLastAssistant]
  );

  // ─── WebSocket frames ─────────────────────────────────────────
  useEffect(() => {
    const unsub = jarvisSocket.onMessage((event: WsEvent) => {
      switch (event.type) {
        case 'start': {
          setIsGenerating(true);
          stepRawRef.current = '';
          ttsSentIndexRef.current = 0;
          ttsQueueRef.current = Promise.resolve();
          ttsAbortedRef.current = false;
          if (event.model) setActiveModel(event.model);
          setMessages((prev) => [
            ...prev,
            {
              id: `assistant-${Date.now()}`,
              role: 'assistant',
              content: '',
              raw: '',
              toolCalls: [],
              blocks: [],
              timestamp: nowLabel(),
              isStreaming: true,
            },
          ]);
          break;
        }

        case 'content': {
          stepRawRef.current += event.content;
          const currentStepRaw = stepRawRef.current;
          const parsed = parseThinkTags(currentStepRaw);

          patchLastAssistant((msg) => {
            msg.raw = (msg.raw || '') + event.content;

            const blocks: MessageBlock[] = msg.blocks ? [...msg.blocks] : [];

            // Find the active thought block or text block in this step (after the last tool_call)
            let lastToolIdx = -1;
            for (let i = blocks.length - 1; i >= 0; i--) {
              if (blocks[i].type === 'tool_call') {
                lastToolIdx = i;
                break;
              }
            }

            // Blocks up to lastToolIdx stay intact
            const prefix = blocks.slice(0, lastToolIdx + 1);
            const stepBlocks: MessageBlock[] = [];

            if (parsed.thought) {
              stepBlocks.push({
                type: 'thought',
                id: `${msg.id}-th-${lastToolIdx + 1}`,
                thought: parsed.thought,
              });
            }
            if (parsed.content) {
              stepBlocks.push({
                type: 'text',
                id: `${msg.id}-tx-${lastToolIdx + 1}`,
                content: parsed.content,
              });
            }

            msg.blocks = [...prefix, ...stepBlocks];

            // Synchronize overall content & thought
            msg.content = msg.blocks
              .filter((b): b is Extract<MessageBlock, { type: 'text' }> => b.type === 'text')
              .map((b) => b.content)
              .join('\n\n');
            msg.thought = msg.blocks
              .filter((b): b is Extract<MessageBlock, { type: 'thought' }> => b.type === 'thought')
              .map((b) => b.thought)
              .join('\n\n');

            return msg;
          });

          // In voice chat mode: early sentence synthesis streaming!
          if (voiceChatRef.current && awaitingReplyRef.current) {
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last && last.role === 'assistant') {
                setVoiceChatAiMsg(last.content);

                // Detect completed sentences in clean unspoken content
                const clean = stripMarkdownForSpeech(last.content);
                const unspoken = clean.slice(ttsSentIndexRef.current);
                const match = unspoken.match(/([.!?]+(?:\s+|\n+)|[\n]{2,})/);
                if (match && match.index !== undefined) {
                  const sentenceEnd = match.index + match[0].length;
                  const sentence = unspoken.slice(0, sentenceEnd).trim();
                  if (sentence.length > 3) {
                    ttsSentIndexRef.current += sentenceEnd;
                    queueSentenceTts(sentence);
                  }
                }
              }
              return prev;
            });
          }
          break;
        }

        case 'tool_call': {
          stepRawRef.current = ''; // Reset for the next step following this tool
          const newTool: ToolCall = {
            id: nextToolId(),
            tool: event.tool,
            args: event.args || {},
            status: 'running',
            startedAt: Date.now(),
          };
          patchLastAssistant((msg) => {
            msg.toolCalls = [...(msg.toolCalls || []), newTool];
            msg.blocks = [
              ...(msg.blocks || []),
              {
                type: 'tool_call',
                id: newTool.id,
                toolCall: newTool,
              },
            ];
            return msg;
          });
          // Show tool name in voice chat overlay
          if (voiceChatRef.current) {
            setVoiceToolName(event.tool || '');
          }
          break;
        }

        case 'ask_user': {
          patchLastAssistant((msg) => {
            const toolCalls = msg.toolCalls || [];
            const lastAsk = [...toolCalls].reverse().find((t) => t.tool === 'ask_user' && t.status === 'running');
            if (lastAsk) {
              lastAsk.prompt_id = event.prompt_id;
              lastAsk.questions = event.questions;
            } else {
              const newTool: ToolCall = {
                id: nextToolId(),
                tool: 'ask_user',
                args: { questions: event.questions },
                status: 'running',
                startedAt: Date.now(),
                prompt_id: event.prompt_id,
                questions: event.questions,
              };
              msg.toolCalls = [...toolCalls, newTool];
              msg.blocks = [
                ...(msg.blocks || []),
                {
                  type: 'tool_call',
                  id: newTool.id,
                  toolCall: newTool,
                },
              ];
            }
            if (msg.blocks) {
              for (const b of msg.blocks) {
                if (b.type === 'tool_call' && b.toolCall.tool === 'ask_user' && b.toolCall.status === 'running') {
                  b.toolCall.prompt_id = event.prompt_id;
                  b.toolCall.questions = event.questions;
                }
              }
            }
            return msg;
          });
          break;
        }

        case 'tool_result':
          resolveToolCall(event.tool, event.result ?? '', !!event.truncated, 'completed');
          break;

        case 'tool_error':
          resolveToolCall(event.tool, event.result ?? '', !!event.truncated, 'error');
          break;

        case 'end': {
          setIsGenerating(false);
          stepRawRef.current = '';
          patchLastAssistant((msg) => {
            msg.isStreaming = false;
            // Anything still "running" at end-of-turn never reported back.
            msg.toolCalls = (msg.toolCalls || []).map((c) =>
              c.status === 'running'
                ? { ...c, status: 'completed', durationMs: Date.now() - c.startedAt }
                : c
            );
            if (msg.blocks) {
              msg.blocks = msg.blocks.map((b) =>
                b.type === 'tool_call' && b.toolCall.status === 'running'
                  ? {
                      ...b,
                      toolCall: {
                        ...b.toolCall,
                        status: 'completed',
                        durationMs: Date.now() - b.toolCall.startedAt,
                      },
                    }
                  : b
              );
            }

            // Capture final AI message for voice chat display
            if (voiceChatRef.current) {
              setVoiceChatAiMsg(msg.content);
            }
            return msg;
          });
          void loadSessions();
          setMessages((current) => {
            const last = current[current.length - 1];
            if (voiceChatRef.current && awaitingReplyRef.current) {
              awaitingReplyRef.current = false;
              if (last && last.role === 'assistant' && last.content) {
                const clean = stripMarkdownForSpeech(last.content);
                const remainder = clean.slice(ttsSentIndexRef.current).trim();
                if (remainder.length > 0) {
                  ttsSentIndexRef.current += remainder.length;
                  queueSentenceTts(remainder);
                }

                ttsQueueRef.current.then(() => {
                  if (voiceChatRef.current && !ttsAbortedRef.current) {
                    setVoiceStatus('listening');
                    setTimeout(() => {
                      if (voiceChatRef.current && !ttsAbortedRef.current) {
                        void beginListeningRef.current();
                      }
                    }, 400);
                  }
                });
              } else {
                setVoiceStatus('listening');
                setTimeout(() => {
                  if (voiceChatRef.current && !ttsAbortedRef.current) {
                    void beginListeningRef.current();
                  }
                }, 400);
              }
            }
            return current;
          });
          break;
        }

        case 'error': {
          setIsGenerating(false);
          patchLastAssistant((msg) => {
            msg.isStreaming = false;
            msg.error = event.message;
            return msg;
          });
          if (voiceChatRef.current) {
            setVoiceStatus('listening');
            setTimeout(() => {
              if (voiceChatRef.current) void beginListeningRef.current();
            }, 500);
          }
          break;
        }

        default:
          break;
      }
    });

    return () => unsub();
  }, [loadSessions, patchLastAssistant, resolveToolCall]);

  // ─── Sending ──────────────────────────────────────────────────

  /** Dispatch a prompt without appending a user bubble (used by regenerate). */
  const dispatchPrompt = useCallback(async (text: string) => {
    lastPromptRef.current = text;
    const sid = sessionIdRef.current;

    if (jarvisSocket.isConnected()) {
      jarvisSocket.send(text, sid);
      return;
    }

    // No socket — fall back to the REST turn, which returns the whole reply.
    setIsGenerating(true);
    let replyText = '';
    try {
      const res = await ChatApi.send(text, sid);
      const parsed = parseThinkTags(res.response || '');
      replyText = parsed.content;
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: parsed.content,
          thought: parsed.thought,
          raw: res.response,
          timestamp: nowLabel(),
        },
      ]);

      // Capture AI response for voice chat
      if (voiceChatRef.current) {
        setVoiceChatAiMsg(parsed.content);
      }

      void loadSessions();
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-error-${Date.now()}`,
          role: 'assistant',
          content: '',
          error: err?.message || 'Connection unavailable.',
          timestamp: nowLabel(),
        },
      ]);
    } finally {
      setIsGenerating(false);
      if (voiceChatRef.current && awaitingReplyRef.current) {
        awaitingReplyRef.current = false;
        if (replyText) {
          queueSentenceTts(replyText);
          ttsQueueRef.current.then(() => {
            if (voiceChatRef.current && !ttsAbortedRef.current) {
              setVoiceStatus('listening');
              setTimeout(() => {
                if (voiceChatRef.current && !ttsAbortedRef.current) {
                  void beginListeningRef.current();
                }
              }, 400);
            }
          });
        } else {
          setVoiceStatus('listening');
          setTimeout(() => {
            if (voiceChatRef.current && !ttsAbortedRef.current) {
              void beginListeningRef.current();
            }
          }, 400);
        }
      }
    }
  }, [loadSessions, queueSentenceTts]);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isGenerating) return;

      // Capture user message for voice chat display
      if (voiceChatRef.current) {
        setVoiceChatUserMsg(trimmed);
        setVoiceChatAiMsg('');
      }

      setMessages((prev) => [
        ...prev,
        {
          id: `user-${Date.now()}`,
          role: 'user',
          content: trimmed,
          timestamp: nowLabel(),
        },
      ]);
      await dispatchPrompt(trimmed);
    },
    [dispatchPrompt, isGenerating]
  );

  // Keep ref in sync for voice callbacks
  useEffect(() => {
    sendMessageRef.current = sendMessage;
  }, [sendMessage]);

  const stopGeneration = useCallback(() => {
    // The engine has no cancel channel yet; drop the socket so no further frames
    // land, then let the ref-counted client reconnect.
    setIsGenerating(false);
    patchLastAssistant((msg) => {
      if (!msg.isStreaming) return msg;
      msg.isStreaming = false;
      msg.error = msg.content ? undefined : 'Stopped.';
      return msg;
    });
    jarvisSocket.reconnectNow();
  }, [patchLastAssistant]);

  const regenerate = useCallback(async () => {
    if (isGenerating) return;
    let prompt = lastPromptRef.current;
    if (!prompt) {
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === 'user') {
          prompt = messages[i].content;
          break;
        }
      }
    }
    if (!prompt) return;

    // Drop the previous assistant turn so the new one replaces it visually.
    setMessages((prev) => {
      const copy = [...prev];
      while (copy.length && copy[copy.length - 1].role === 'assistant') copy.pop();
      return copy;
    });
    await dispatchPrompt(prompt);
  }, [dispatchPrompt, isGenerating, messages]);

  const editAndResend = useCallback(
    async (messageId: string, newText: string) => {
      const trimmed = newText.trim();
      if (!trimmed || isGenerating) return;

      setMessages((prev) => {
        const idx = prev.findIndex((m) => m.id === messageId);
        if (idx === -1) return prev;
        const kept = prev.slice(0, idx);
        return [...kept, { ...prev[idx], content: trimmed, timestamp: nowLabel() }];
      });
      await dispatchPrompt(trimmed);
    },
    [dispatchPrompt, isGenerating]
  );

  // ─── Voice (legacy overlay mode — kept for backward compat) ───
  const startVoiceMode = useCallback(async () => {
    try {
      setIsVoiceMode(true);
      setLiveVoiceTranscript('');
      await audioService.startRecording(publishAudioLevels, setLiveVoiceTranscript);
    } catch (e: any) {
      console.error('Failed to start voice mode:', e);
      setIsVoiceMode(false);
      publishAudioLevels(EMPTY_LEVELS);
      throw new Error(e?.message || 'Microphone access was denied.');
    }
  }, [publishAudioLevels]);

  const stopVoiceMode = useCallback(async () => {
    try {
      setVoiceTranscribing(true);
      const audioBlob = await audioService.stopRecording();
      setIsVoiceMode(false);
      publishAudioLevels(EMPTY_LEVELS);

      let text = liveVoiceTranscript.trim();

      if (!text && audioBlob && audioBlob.size > 0) {
        try {
          const res = await VoiceApi.transcribe(audioBlob);
          text = res.text.trim();
        } catch (err) {
          console.warn('Backend transcription failed:', err);
        }
      }

      setVoiceTranscribing(false);
      setLiveVoiceTranscript('');

      if (text) await sendMessage(text);
    } catch (e) {
      console.error('Failed to stop voice recording:', e);
      setIsVoiceMode(false);
      setVoiceTranscribing(false);
      publishAudioLevels(EMPTY_LEVELS);
    }
  }, [liveVoiceTranscript, publishAudioLevels, sendMessage]);

  const cancelVoiceMode = useCallback(() => {
    audioService.cancelRecording();
    setIsVoiceMode(false);
    setVoiceTranscribing(false);
    setLiveVoiceTranscript('');
    publishAudioLevels(EMPTY_LEVELS);
  }, [publishAudioLevels]);



  // ─── Voice Chat (inline, auto-send mode) ──────────────────────

  /** Start a voice recording round with VAD for auto-send. */
  const beginVoiceListening = useCallback(async () => {
    if (!voiceChatRef.current) return;
    try {
      setIsVoiceMode(true);
      setVoiceStatus('listening');
      setLiveVoiceTranscript('');
      liveTranscriptRef.current = '';
      await audioService.startRecording(
        publishAudioLevels,
        (text) => {
          liveTranscriptRef.current = text;
          setLiveVoiceTranscript(text);
          if (text) {
            setVoiceChatAiMsg('');
            setVoiceChatUserMsg(text);
          }
        },
        {
          // VAD: auto-finalise when speech ends
          onSpeechEnd: () => {
            void finaliseUtteranceRef.current();
          },
        }
      );
    } catch (e: any) {
      console.error('Voice chat: failed to start listening:', e);
      setIsVoiceMode(false);
      setVoiceStatus('idle');
      setVoiceError(e?.message || 'Microphone access was denied.');
    }
  }, [publishAudioLevels]);

  /** Finalise an utterance: stop recording, transcribe, send, then wait for reply. */
  const finaliseUtterance = useCallback(async () => {
    if (!voiceChatRef.current) return;
    try {
      setVoiceStatus('transcribing');
      setVoiceTranscribing(true);
      const audioBlob = await audioService.stopRecording();
      setIsVoiceMode(false);
      publishAudioLevels(EMPTY_LEVELS);

      let text = liveTranscriptRef.current.trim() || audioService.getLatestTranscript().trim();

      if (!text && audioBlob && audioBlob.size > 0) {
        try {
          const res = await VoiceApi.transcribe(audioBlob);
          text = res.text.trim();
        } catch (err) {
          console.warn('Backend transcription failed:', err);
        }
      }

      setVoiceTranscribing(false);
      setLiveVoiceTranscript('');

      if (text) {
        setVoiceChatUserMsg(text);
        setVoiceChatAiMsg('');
        setVoiceToolName('');
        setVoiceStatus('thinking');
        awaitingReplyRef.current = true;
        ttsAbortedRef.current = false;
        ttsSentIndexRef.current = 0;
        ttsQueueRef.current = Promise.resolve();
        await sendMessageRef.current(text);
      } else {
        // No speech detected — resume listening
        if (voiceChatRef.current) {
          void beginListeningRef.current();
        }
      }
    } catch (e) {
      console.error('Voice chat: finalise failed:', e);
      setIsVoiceMode(false);
      setVoiceTranscribing(false);
      setVoiceStatus('idle');
      publishAudioLevels(EMPTY_LEVELS);
      // Try to resume listening
      if (voiceChatRef.current) {
        setTimeout(() => void beginListeningRef.current(), 500);
      }
    }
  }, [publishAudioLevels]);

  // Keep refs in sync
  useEffect(() => {
    beginListeningRef.current = beginVoiceListening;
  }, [beginVoiceListening]);

  useEffect(() => {
    finaliseUtteranceRef.current = finaliseUtterance;
  }, [finaliseUtterance]);

  const startVoiceChat = useCallback(async () => {
    voiceChatRef.current = true;
    ttsAbortedRef.current = false;
    ttsSentIndexRef.current = 0;
    ttsQueueRef.current = Promise.resolve();
    setIsVoiceChatActive(true);
    setVoiceChatUserMsg('');
    setVoiceChatAiMsg('');
    setVoiceError('');
    await beginVoiceListening();
  }, [beginVoiceListening]);

  const endVoiceChat = useCallback(() => {
    voiceChatRef.current = false;
    awaitingReplyRef.current = false;
    ttsAbortedRef.current = true;
    ttsSentIndexRef.current = 0;
    ttsQueueRef.current = Promise.resolve();
    setIsVoiceChatActive(false);
    setVoiceStatus('idle');
    setVoiceChatUserMsg('');
    setVoiceChatAiMsg('');
    setLiveVoiceTranscript('');
    audioService.cancelRecording();
    audioService.stopAudio();
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setIsVoiceMode(false);
    setVoiceTranscribing(false);
    publishAudioLevels(EMPTY_LEVELS);
  }, [publishAudioLevels]);

  /** Stop TTS playback without leaving voice mode — resumes listening. */
  const stopTts = useCallback(() => {
    ttsAbortedRef.current = true;
    ttsSentIndexRef.current = 0;
    ttsQueueRef.current = Promise.resolve();
    audioService.stopAudio();
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setVoiceStatus('listening');
    // Reset abort flag after a tick so new TTS for the next turn can proceed
    setTimeout(() => {
      if (voiceChatRef.current) {
        ttsAbortedRef.current = false;
        void beginListeningRef.current();
      }
    }, 200);
  }, []);

  // Legacy voice session stubs (kept for any other consumers)
  const startVoiceSession = useCallback(async () => {
    await startVoiceChat();
  }, [startVoiceChat]);

  const endVoiceSession = useCallback(() => {
    endVoiceChat();
  }, [endVoiceChat]);

  // Never leave the mic hot if the provider unmounts.
  useEffect(() => () => audioService.cancelRecording(), []);

  const respondToAskUser = useCallback((promptId: string, response: any) => {
    jarvisSocket.sendEvent({
      type: 'ask_user_response',
      prompt_id: promptId,
      response,
    });
  }, []);

  const value = useMemo<JarvisContextType>(
    () => ({
      messages,
      isGenerating,
      connectionState,
      activeModel,
      activeProvider,
      reasoningEffort,
      userName,
      sendMessage,
      stopGeneration,
      regenerate,
      editAndResend,
      clearActiveChat,
      updateActiveModel,
      setReasoningEffort,
      setUserName,
      reconnect,
      respondToAskUser,
      sessions,
      currentSessionId,
      isDrawerOpen,
      setDrawerOpen,
      toggleDrawer,
      selectSession,
      createNewSession,
      deleteSession,
      renameSession,
      loadSessions,
      isVoiceMode,
      voiceTranscribing,
      isVoiceChatActive,
      isVoiceSession,
      voiceStatus,
      voiceError,
      liveVoiceTranscript,
      voiceChatUserMsg,
      voiceChatAiMsg,
      voiceToolName,
      startVoiceChat,
      endVoiceChat,
      stopTts,
      startVoiceSession,
      endVoiceSession,
      subscribeToAudioLevels,
      getAudioLevels,
    }),
    [
      messages,
      isGenerating,
      connectionState,
      activeModel,
      activeProvider,
      reasoningEffort,
      userName,
      sendMessage,
      stopGeneration,
      regenerate,
      editAndResend,
      clearActiveChat,
      updateActiveModel,
      setReasoningEffort,
      setUserName,
      reconnect,
      respondToAskUser,
      sessions,
      currentSessionId,
      isDrawerOpen,
      toggleDrawer,
      selectSession,
      createNewSession,
      deleteSession,
      renameSession,
      loadSessions,
      isVoiceMode,
      voiceTranscribing,
      isVoiceChatActive,
      isVoiceSession,
      voiceStatus,
      voiceError,
      liveVoiceTranscript,
      voiceChatUserMsg,
      voiceChatAiMsg,
      voiceToolName,
      startVoiceChat,
      endVoiceChat,
      stopTts,
      startVoiceSession,
      endVoiceSession,
      subscribeToAudioLevels,
      getAudioLevels,
    ]
  );

  return <JarvisContext.Provider value={value}>{children}</JarvisContext.Provider>;
};

export const useJarvis = (): JarvisContextType => {
  const context = useContext(JarvisContext);
  if (!context) throw new Error('useJarvis must be used within JarvisProvider');
  return context;
};
