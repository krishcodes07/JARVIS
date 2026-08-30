import React, { useEffect, useRef, useState } from 'react';
import { Check, Menu, Mic, Plus, RefreshCw, Settings2, X } from 'lucide-react';
import { useJarvis } from '../../context/JarvisContext';
import { ConnectionState, SettingsTab } from '../../types';
import { cn } from '../../utils/cn';
import { IconButton, Tooltip } from '../ui';

export interface TopBarProps {
  onOpenSettings: (tab?: SettingsTab) => void;
  onOpenDrawer: () => void;
  onNewChat?: () => void;
}

const CONNECTION_COPY: Record<ConnectionState, { label: string; dot: string; tone: string }> = {
  open: { label: 'Connected', dot: 'bg-success', tone: 'text-success' },
  connecting: { label: 'Connecting…', dot: 'bg-warning animate-pulse', tone: 'text-warning' },
  closed: { label: 'Disconnected — click to retry', dot: 'bg-danger', tone: 'text-danger' },
};

/** Compact model + effort pill; clicking deep-links into Model settings. */
const ModelPill: React.FC<{ onClick: () => void }> = ({ onClick }) => {
  const { activeModel, activeProvider, reasoningEffort } = useJarvis();
  const showEffort = reasoningEffort && reasoningEffort !== 'none';

  return (
    <Tooltip label="Model & reasoning settings" side="bottom">
      <button
        onClick={onClick}
        className="flex max-w-[45vw] items-center gap-2 rounded-lg border border-subtle/12 bg-surface-2/60 px-2.5 py-1.5 text-xs transition-colors hover:border-accent/35 hover:bg-surface-2"
      >
        <Settings2 className="h-3.5 w-3.5 shrink-0 text-accent" />
        <span className="truncate font-medium text-content">
          {activeModel || activeProvider || 'No model'}
        </span>
        {showEffort && (
          <>
            <span className="text-content-muted/60">·</span>
            <span className="shrink-0 uppercase tracking-wide text-accent">{reasoningEffort}</span>
          </>
        )}
      </button>
    </Tooltip>
  );
};

/** Session title with inline rename. */
const SessionTitle: React.FC = () => {
  const { sessions, currentSessionId, renameSession } = useJarvis();
  if (!currentSessionId) return null;

  const session = sessions.find((s) => s.session_id === currentSessionId);
  const title = session?.title || 'New conversation';

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!editing) setDraft(title);
  }, [title, editing]);

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  const commit = () => {
    const next = draft.trim();
    setEditing(false);
    if (session && next && next !== title) renameSession(session.session_id, next);
  };

  if (!session) {
    return <span className="truncate text-sm font-medium text-content-muted">{title}</span>;
  }

  if (editing) {
    return (
      <div className="flex min-w-0 items-center gap-1">
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit();
            if (e.key === 'Escape') {
              setDraft(title);
              setEditing(false);
            }
          }}
          onBlur={commit}
          className="min-w-0 flex-1 rounded-md bg-surface-2/80 px-2 py-1 text-sm text-content outline-none ring-1 ring-accent/40"
        />
        <IconButton label="Save title" size="xs" tooltip={false} onMouseDown={commit}>
          <Check />
        </IconButton>
      </div>
    );
  }

  return (
    <button
      onClick={() => setEditing(true)}
      title="Rename conversation"
      className="min-w-0 truncate rounded-md px-1.5 py-1 text-left text-sm font-medium text-content transition-colors hover:bg-surface-2/60"
    >
      {title}
    </button>
  );
};

export const TopBar: React.FC<TopBarProps> = ({ onOpenSettings, onOpenDrawer, onNewChat }) => {
  const {
    connectionState,
    reconnect,
    isVoiceChatActive,
    startVoiceChat,
    endVoiceChat,
    clearActiveChat,
  } = useJarvis();

  const conn = CONNECTION_COPY[connectionState];

  const handleVoice = () => {
    if (isVoiceChatActive) endVoiceChat();
    else void startVoiceChat().catch((e) => console.warn(e));
  };

  return (
    <header
      data-chrome
      className="relative z-20 flex h-14 shrink-0 items-center gap-2 border-b border-subtle/8 bg-surface-3/50 px-3 backdrop-blur-xl sm:px-4"
    >
      <IconButton
        label="Open menu"
        size="sm"
        tooltip={false}
        className="lg:hidden"
        onClick={onOpenDrawer}
      >
        <Menu />
      </IconButton>

      <div className="min-w-0 flex-1">
        <SessionTitle />
      </div>

      <div className="flex shrink-0 items-center gap-1.5">
        <div className="hidden sm:block">
          <ModelPill onClick={() => onOpenSettings('model')} />
        </div>

        <Tooltip label={conn.label} side="bottom">
          <button
            onClick={connectionState === 'closed' ? reconnect : undefined}
            aria-label={conn.label}
            className={cn(
              'flex h-8 items-center gap-1.5 rounded-lg px-2 transition-colors',
              connectionState === 'closed'
                ? 'hover:bg-danger/12'
                : 'cursor-default hover:bg-surface-2/50'
            )}
          >
            <span className={cn('h-2 w-2 rounded-full', conn.dot)} />
            {connectionState === 'closed' && (
              <RefreshCw className={cn('h-3 w-3', conn.tone)} />
            )}
          </button>
        </Tooltip>

        <IconButton
          label={isVoiceChatActive ? 'Exit voice chat' : 'Voice chat'}
          size="sm"
          tooltip="bottom"
          active={isVoiceChatActive}
          onClick={handleVoice}
        >
          {isVoiceChatActive ? <X /> : <Mic />}
        </IconButton>

        <IconButton
          label="New chat"
          size="sm"
          tooltip="bottom"
          className="sm:hidden"
          onClick={() => {
            if (onNewChat) onNewChat();
            else clearActiveChat();
          }}
        >
          <Plus />
        </IconButton>
      </div>
    </header>
  );
};
