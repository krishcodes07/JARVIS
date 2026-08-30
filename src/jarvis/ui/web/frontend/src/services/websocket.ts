import { ConnectionState, WsEvent } from '../types';

type MessageHandler = (event: WsEvent) => void;
type StateHandler = (state: ConnectionState) => void;

/** Base reconnect delay; doubles per attempt up to MAX_BACKOFF_MS. */
const BASE_BACKOFF_MS = 500;
const MAX_BACKOFF_MS = 15_000;
/** Keeps intermediaries from idling the socket out. */
const HEARTBEAT_MS = 25_000;
/** How long an outbound message waits for a connection before giving up. */
const SEND_TIMEOUT_MS = 5_000;

/**
 * Single long-lived connection to `/api/chat/ws`.
 *
 * Lifecycle is ref-counted rather than boolean-flagged: React StrictMode mounts
 * effects twice, so a plain `isExplicitClose` latch would permanently disable
 * auto-reconnect after the first simulated unmount.
 */
export class JarvisWebSocketClient {
  private ws: WebSocket | null = null;
  private handlers = new Set<MessageHandler>();
  private stateHandlers = new Set<StateHandler>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private attempt = 0;
  private refCount = 0;
  private state: ConnectionState = 'closed';
  private queue: string[] = [];

  private getWsUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/api/chat/ws`;
  }

  // ── State ──────────────────────────────────────────────────────
  public getState(): ConnectionState {
    return this.state;
  }

  public isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private setState(next: ConnectionState): void {
    if (this.state === next) return;
    this.state = next;
    this.stateHandlers.forEach((fn) => fn(next));
  }

  public onStateChange(handler: StateHandler): () => void {
    this.stateHandlers.add(handler);
    handler(this.state);
    return () => {
      this.stateHandlers.delete(handler);
    };
  }

  public onMessage(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }

  // ── Lifecycle ──────────────────────────────────────────────────

  /**
   * Acquire the connection. Returns a release function; the socket is only torn
   * down once every acquirer has released it.
   */
  public acquire(): () => void {
    this.refCount += 1;
    this.connect();
    let released = false;
    return () => {
      if (released) return;
      released = true;
      this.refCount = Math.max(0, this.refCount - 1);
      if (this.refCount === 0) this.teardown();
    };
  }

  public connect(): void {
    const rs = this.ws?.readyState;
    if (rs === WebSocket.OPEN || rs === WebSocket.CONNECTING) return;

    this.clearReconnect();
    this.setState('connecting');

    let socket: WebSocket;
    try {
      socket = new WebSocket(this.getWsUrl());
    } catch {
      this.scheduleReconnect();
      return;
    }
    this.ws = socket;

    socket.onopen = () => {
      if (this.ws !== socket) return;
      this.attempt = 0;
      this.setState('open');
      this.startHeartbeat();
      this.flushQueue();
    };

    socket.onmessage = (event) => {
      if (this.ws !== socket) return;
      let parsed: unknown;
      try {
        parsed = JSON.parse(event.data);
      } catch {
        return; // non-JSON frame; nothing meaningful to dispatch
      }
      if (!parsed || typeof parsed !== 'object' || !('type' in parsed)) return;
      const frame = parsed as WsEvent;
      if (frame.type === 'pong') return;
      this.handlers.forEach((fn) => fn(frame));
    };

    socket.onclose = () => {
      if (this.ws !== socket) return;
      this.ws = null;
      this.stopHeartbeat();
      this.setState('closed');
      if (this.refCount > 0) this.scheduleReconnect();
    };

    socket.onerror = () => {
      // Close always follows an error; reconnect is handled there.
    };
  }

  /** Close the socket and stop reconnecting. Called when the last ref releases. */
  private teardown(): void {
    this.clearReconnect();
    this.stopHeartbeat();
    this.queue = [];
    const socket = this.ws;
    this.ws = null;
    if (socket) {
      socket.onopen = socket.onmessage = socket.onclose = socket.onerror = null;
      try {
        socket.close();
      } catch {
        // already closing
      }
    }
    this.setState('closed');
  }

  /** Force a reconnect now (used by a manual "retry" affordance). */
  public reconnectNow(): void {
    this.attempt = 0;
    this.clearReconnect();
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        // ignore
      }
      this.ws = null;
    }
    this.connect();
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer || this.refCount === 0) return;
    const backoff = Math.min(BASE_BACKOFF_MS * 2 ** this.attempt, MAX_BACKOFF_MS);
    // Jitter avoids a thundering herd when several tabs reconnect together.
    const delay = backoff * (0.7 + Math.random() * 0.6);
    this.attempt += 1;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private clearReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ type: 'ping' }));
        } catch {
          // socket is going away; onclose will reconnect
        }
      }
    }, HEARTBEAT_MS);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  // ── Sending ────────────────────────────────────────────────────

  public send(message: string, sessionId?: string): void {
    const payload = JSON.stringify({ type: 'message', message, session_id: sessionId });
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(payload);
      return;
    }
    // Buffer and let onopen flush it, so a send during reconnect isn't lost.
    this.queue.push(payload);
    setTimeout(() => {
      const idx = this.queue.indexOf(payload);
      if (idx !== -1) this.queue.splice(idx, 1);
    }, SEND_TIMEOUT_MS);
    this.connect();
  }

  public sendEvent(event: Record<string, any>): void {
    const payload = JSON.stringify(event);
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(payload);
      return;
    }
    this.queue.push(payload);
    setTimeout(() => {
      const idx = this.queue.indexOf(payload);
      if (idx !== -1) this.queue.splice(idx, 1);
    }, SEND_TIMEOUT_MS);
    this.connect();
  }

  /** @deprecated Use {@link send}. */
  public sendMessage(message: string, sessionId?: string): void {
    this.send(message, sessionId);
  }

  private flushQueue(): void {
    if (!this.queue.length || this.ws?.readyState !== WebSocket.OPEN) return;
    const pending = this.queue;
    this.queue = [];
    for (const payload of pending) {
      try {
        this.ws.send(payload);
      } catch {
        break;
      }
    }
  }
}

export const jarvisSocket = new JarvisWebSocketClient();
