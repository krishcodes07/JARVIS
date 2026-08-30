import React, { memo, useEffect, useRef, useState } from 'react';
import { AlertTriangle, Check, Copy, Pencil, RefreshCw, X } from 'lucide-react';
import { ChatMessage } from '../../types';
import { MarkdownRenderer } from '../../utils/markdown';
import { OrbAvatar } from '../JarvisBlob';
import { Button, IconButton } from '../ui';
import { ThinkingBlock } from './ThinkingBlock';
import { ToolCallPill } from './ToolCallPill';

export interface MessageItemProps {
  message: ChatMessage;
  /** Enables regenerate on the trailing assistant turn. */
  isLast: boolean;
  onRegenerate: () => void;
  onEdit: (id: string, text: string) => void;
}

function useCopy() {
  const [copied, setCopied] = useState(false);
  const copy = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard API needs a secure context; nothing useful to do here.
    }
  };
  return { copied, copy };
}

// ─── User turn ────────────────────────────────────────────────────

const UserMessage: React.FC<{
  message: ChatMessage;
  onEdit: (id: string, text: string) => void;
}> = ({ message, onEdit }) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(message.content);
  const areaRef = useRef<HTMLTextAreaElement>(null);
  const { copied, copy } = useCopy();

  useEffect(() => {
    if (editing) {
      const el = areaRef.current;
      if (!el) return;
      el.focus();
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 240)}px`;
      el.setSelectionRange(el.value.length, el.value.length);
    }
  }, [editing]);

  if (editing) {
    return (
      <div className="group flex flex-col items-end gap-2">
        <div className="w-full max-w-[85%] rounded-2xl border border-accent/40 bg-surface-2/80 p-2.5">
          <textarea
            ref={areaRef}
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = `${Math.min(e.target.scrollHeight, 240)}px`;
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                setEditing(false);
                onEdit(message.id, draft);
              }
              if (e.key === 'Escape') {
                setDraft(message.content);
                setEditing(false);
              }
            }}
            className="scroll-area w-full resize-none bg-transparent text-[15px] leading-6 text-content outline-none"
          />
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            icon={<X />}
            onClick={() => {
              setDraft(message.content);
              setEditing(false);
            }}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            variant="primary"
            icon={<RefreshCw />}
            disabled={!draft.trim()}
            onClick={() => {
              setEditing(false);
              onEdit(message.id, draft);
            }}
          >
            Send
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="group flex flex-col items-end gap-1">
      <div className="max-w-[85%] rounded-2xl rounded-br-md border border-accent/18 bg-accent/[0.10] px-4 py-2.5">
        <p className="whitespace-pre-wrap break-words text-[15px] font-[450] leading-6 text-content">
          {message.content}
        </p>
      </div>
      <div className="flex items-center gap-0.5 pr-1 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
        <IconButton
          label={copied ? 'Copied' : 'Copy'}
          size="xs"
          onClick={() => copy(message.content)}
        >
          {copied ? <Check /> : <Copy />}
        </IconButton>
        <IconButton label="Edit and resend" size="xs" onClick={() => setEditing(true)}>
          <Pencil />
        </IconButton>
      </div>
    </div>
  );
};

// ─── Assistant turn ───────────────────────────────────────────────

const AssistantMessage: React.FC<{
  message: ChatMessage;
  isLast: boolean;
  onRegenerate: () => void;
}> = ({ message, isLast, onRegenerate }) => {
  const { copied, copy } = useCopy();
  const hasBlocks = !!message.blocks && message.blocks.length > 0;
  const empty =
    !hasBlocks && !message.content && !message.thought && !message.toolCalls?.length;

  return (
    <div className="group flex gap-3">
      <div className="pt-0.5">
        <OrbAvatar size={30} />
      </div>

      <div className="min-w-0 flex-1">
        {hasBlocks ? (
          message.blocks!.map((block, idx) => {
            if (block.type === 'thought') {
              return (
                <ThinkingBlock
                  key={block.id || idx}
                  thought={block.thought}
                  isStreaming={message.isStreaming && idx === message.blocks!.length - 1}
                />
              );
            }
            if (block.type === 'tool_call') {
              return <ToolCallPill key={block.id || idx} toolCall={block.toolCall} />;
            }
            if (block.type === 'text') {
              return <MarkdownRenderer key={block.id || idx} content={block.content} />;
            }
            return null;
          })
        ) : (
          <>
            {message.thought !== undefined && message.thought !== '' && (
              <ThinkingBlock thought={message.thought} isStreaming={message.isStreaming} />
            )}

            {message.toolCalls?.map((call) => <ToolCallPill key={call.id} toolCall={call} />)}

            {message.content && <MarkdownRenderer content={message.content} />}
          </>
        )}

        {message.isStreaming && (
          <span className="inline-flex items-center gap-2">
            {empty && <span className="text-sm text-content-muted">Working…</span>}
            <span className="inline-block h-4 w-[2px] animate-caret-blink bg-accent align-middle" />
          </span>
        )}

        {message.error && (
          <div className="mt-2 flex items-start gap-2 rounded-xl border border-danger/25 bg-danger/[0.08] px-3 py-2.5">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
            <div className="min-w-0 flex-1 text-xs leading-relaxed text-danger">
              {message.error}
            </div>
            <button
              onClick={onRegenerate}
              className="shrink-0 text-xs font-medium text-danger underline decoration-danger/40 underline-offset-2 hover:decoration-danger"
            >
              Retry
            </button>
          </div>
        )}

        {!message.isStreaming && (message.content || hasBlocks || message.error) && (
          <div className="mt-1 flex items-center gap-0.5 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
            <IconButton
              label={copied ? 'Copied' : 'Copy response'}
              size="xs"
              onClick={() => copy(message.content)}
            >
              {copied ? <Check /> : <Copy />}
            </IconButton>
            {isLast && (
              <IconButton label="Regenerate" size="xs" onClick={onRegenerate}>
                <RefreshCw />
              </IconButton>
            )}
            {message.timestamp && (
              <span className="ml-1.5 text-[10px] text-content-muted">{message.timestamp}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Dispatcher ───────────────────────────────────────────────────

export const MessageItem: React.FC<MessageItemProps> = memo(
  ({ message, isLast, onRegenerate, onEdit }) => {
    if (message.role === 'user') {
      return <UserMessage message={message} onEdit={onEdit} />;
    }

    if (message.role === 'system') {
      return (
        <div className="flex justify-center">
          <span className="rounded-full border border-subtle/12 bg-surface-2/60 px-3 py-1 text-[11px] text-content-muted">
            {message.content}
          </span>
        </div>
      );
    }

    if (message.role === 'tool') {
      return null;
    }

    return (
      <AssistantMessage message={message} isLast={isLast} onRegenerate={onRegenerate} />
    );
  }
);
MessageItem.displayName = 'MessageItem';
