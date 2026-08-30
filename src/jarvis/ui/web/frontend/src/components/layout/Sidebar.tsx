import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Check,
  ChevronsLeft,
  ChevronsRight,
  MessageSquarePlus,
  Pencil,
  Search,
  Settings,
  Trash2,
  X,
} from 'lucide-react';
import { useJarvis } from '../../context/JarvisContext';
import { useTheme } from '../../context/ThemeContext';
import { SessionSummary, SettingsTab } from '../../types';
import { cn } from '../../utils/cn';
import { Button, IconButton, Modal } from '../ui';

const MIN_WIDTH = 220;
const MAX_WIDTH = 480;
const DEFAULT_EXPANDED_WIDTH = 264;
const RAIL_WIDTH = 68;

export interface SidebarProps {
  onOpenSettings: (tab?: SettingsTab) => void;
  /** Override session selection — used by ChatView for route-aware navigation. */
  onSelectSession?: (sid: string) => Promise<void>;
  /** Override new session — used by ChatView for route-aware navigation. */
  onNewSession?: () => Promise<void>;
  /** Mobile drawer: renders always-expanded and closes on selection. */
  variant?: 'docked' | 'drawer';
  onRequestClose?: () => void;
}

// ─── Date grouping ────────────────────────────────────────────────

const GROUP_ORDER = ['Today', 'Yesterday', 'Previous 7 days', 'Older'] as const;
type GroupName = (typeof GROUP_ORDER)[number];

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

function groupFor(iso: string): GroupName {
  const ts = Date.parse(iso);
  if (!Number.isFinite(ts)) return 'Older';
  const today = startOfDay(new Date());
  const day = startOfDay(new Date(ts));
  const diffDays = Math.round((today - day) / 86_400_000);
  if (diffDays <= 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays <= 7) return 'Previous 7 days';
  return 'Older';
}

function groupSessions(sessions: SessionSummary[]): Array<[GroupName, SessionSummary[]]> {
  const buckets = new Map<GroupName, SessionSummary[]>();
  for (const s of sessions) {
    const key = groupFor(s.updated_at);
    const list = buckets.get(key);
    if (list) list.push(s);
    else buckets.set(key, [s]);
  }
  return GROUP_ORDER.filter((g) => buckets.get(g)?.length).map(
    (g) => [g, buckets.get(g)!] as [GroupName, SessionSummary[]]
  );
}

// ─── Session row ──────────────────────────────────────────────────

interface SessionRowProps {
  session: SessionSummary;
  active: boolean;
  onSelect: () => void;
  onRename: (title: string) => void;
  onRequestDelete: () => void;
}

const SessionRow: React.FC<SessionRowProps> = ({
  session,
  active,
  onSelect,
  onRename,
  onRequestDelete,
}) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(session.title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  const commit = () => {
    const next = draft.trim();
    setEditing(false);
    if (next && next !== session.title) onRename(next);
    else setDraft(session.title);
  };

  if (editing) {
    return (
      <div className="flex items-center gap-1 rounded-lg bg-surface-2/80 px-2 py-1.5 ring-1 ring-accent/40">
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit();
            if (e.key === 'Escape') {
              setDraft(session.title);
              setEditing(false);
            }
          }}
          onBlur={commit}
          className="min-w-0 flex-1 bg-transparent text-[13px] text-content outline-none"
        />
        <IconButton label="Save title" size="xs" tooltip={false} onMouseDown={commit}>
          <Check />
        </IconButton>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'group relative flex items-center rounded-lg transition-colors duration-150',
        active ? 'bg-accent/12 text-content' : 'text-content-secondary hover:bg-surface-2/60'
      )}
    >
      {active && (
        <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-r bg-accent" />
      )}
      <button
        onClick={onSelect}
        className="min-w-0 flex-1 truncate px-3 py-2 text-left text-[13px] leading-tight"
        title={session.title}
      >
        {session.title || 'Untitled'}
      </button>
      <div className="flex shrink-0 items-center pr-1 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
        <IconButton
          label="Rename"
          size="xs"
          tooltip={false}
          onClick={() => {
            setDraft(session.title);
            setEditing(true);
          }}
        >
          <Pencil />
        </IconButton>
        <IconButton label="Delete" size="xs" tone="danger" tooltip={false} onClick={onRequestDelete}>
          <Trash2 />
        </IconButton>
      </div>
    </div>
  );
};

// ─── Sidebar ──────────────────────────────────────────────────────

/**
 * Session navigator. Collapses to an icon rail on desktop; the mobile drawer
 * reuses the same component in its always-expanded `drawer` variant.
 * Supports drag-to-resize in docked mode.
 */
export const Sidebar: React.FC<SidebarProps> = ({
  onOpenSettings,
  onSelectSession,
  onNewSession,
  variant = 'docked',
  onRequestClose,
}) => {
  const {
    sessions,
    currentSessionId,
    selectSession,
    createNewSession,
    deleteSession,
    renameSession,
    activeModel,
    userName,
  } = useJarvis();
  const { sidebarExpanded, setSidebarExpanded, enableAnimations } = useTheme();

  const isDrawer = variant === 'drawer';
  const expanded = isDrawer || sidebarExpanded;

  const [query, setQuery] = useState('');
  const [pendingDelete, setPendingDelete] = useState<SessionSummary | null>(null);
  const [busy, setBusy] = useState(false);

  // ─── Drag-to-resize ───────────────────────────────────────────
  const [sidebarWidth, setSidebarWidth] = useState(DEFAULT_EXPANDED_WIDTH);
  const isDragging = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(DEFAULT_EXPANDED_WIDTH);

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDragging.current = true;
    startX.current = e.clientX;
    startWidth.current = sidebarWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const handleDragMove = (ev: MouseEvent) => {
      if (!isDragging.current) return;
      const delta = ev.clientX - startX.current;
      const newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, startWidth.current + delta));
      setSidebarWidth(newWidth);
      document.documentElement.style.setProperty('--sidebar-width', `${newWidth}px`);
    };

    const handleDragEnd = () => {
      isDragging.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', handleDragMove);
      document.removeEventListener('mouseup', handleDragEnd);
    };

    document.addEventListener('mousemove', handleDragMove);
    document.addEventListener('mouseup', handleDragEnd);
  }, [sidebarWidth]);

  useEffect(() => {
    if (expanded && !isDrawer) {
      document.documentElement.style.setProperty('--sidebar-width', `${sidebarWidth}px`);
    } else {
      document.documentElement.style.setProperty('--sidebar-width', '0px');
    }
  }, [expanded, isDrawer, sidebarWidth]);

  const groups = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const filtered = needle
      ? sessions.filter((s) => s.title.toLowerCase().includes(needle))
      : sessions;
    return groupSessions(filtered);
  }, [sessions, query]);

  const handleSelect = async (sid: string) => {
    if (onSelectSession) {
      await onSelectSession(sid);
    } else {
      await selectSession(sid);
    }
    onRequestClose?.();
  };

  const handleNew = async () => {
    setBusy(true);
    try {
      if (onNewSession) {
        await onNewSession();
      } else {
        await createNewSession();
      }
      onRequestClose?.();
    } finally {
      setBusy(false);
    }
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    const target = pendingDelete;
    setPendingDelete(null);
    await deleteSession(target.session_id);
  };

  const currentWidth = isDrawer
    ? DEFAULT_EXPANDED_WIDTH
    : expanded
      ? sidebarWidth
      : RAIL_WIDTH;

  return (
    <>
      <motion.aside
        data-chrome
        initial={false}
        animate={{ width: currentWidth }}
        transition={
          enableAnimations ? { duration: 0.24, ease: [0.22, 1, 0.36, 1] } : { duration: 0 }
        }
        className={cn(
          'relative z-30 h-full shrink-0 flex-col overflow-hidden',
          expanded
            ? 'border-r border-subtle/12 bg-surface-3'
            : 'border-r border-subtle/8 bg-surface-3/50 backdrop-blur-xl',
          // Below `lg` the docked rail is replaced by SidebarDrawer.
          isDrawer ? 'flex' : 'hidden lg:flex'
        )}
        style={isDrawer ? { width: DEFAULT_EXPANDED_WIDTH } : undefined}
      >
        {/* Brand + collapse */}
        <div className="flex h-14 items-center gap-2 px-3">
          {expanded && (
            <span className="min-w-0 flex-1 truncate font-display text-sm font-semibold tracking-wide text-content">
              JARVIS
            </span>
          )}
          {isDrawer ? (
            <IconButton label="Close menu" size="sm" tooltip={false} onClick={onRequestClose}>
              <X />
            </IconButton>
          ) : (
            <IconButton
              label={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
              size="sm"
              tooltip="right"
              onClick={() => setSidebarExpanded(!expanded)}
              className={cn(expanded ? 'ml-auto' : 'mx-auto')}
            >
              {expanded ? <ChevronsLeft /> : <ChevronsRight />}
            </IconButton>
          )}
        </div>

        {/* New chat (expanded only) */}
        {expanded && (
          <div className="px-3 pb-3">
            <Button
              variant="primary"
              size="md"
              fullWidth
              loading={busy}
              icon={<MessageSquarePlus />}
              onClick={handleNew}
            >
              New chat
            </Button>
          </div>
        )}

        {/* Search */}
        {expanded && (
          <div className="px-3 pb-2">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-content-muted" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search chats"
                className="h-9 w-full rounded-lg border border-subtle/12 bg-surface-2/60 pl-9 pr-8 text-xs text-content placeholder:text-content-muted/70 transition-colors focus:border-accent/50 focus:outline-none"
              />
              {query && (
                <button
                  onClick={() => setQuery('')}
                  aria-label="Clear search"
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-content-muted hover:text-content"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Sessions */}
        <div className="scroll-area min-h-0 flex-1 overflow-y-auto px-3 pb-2">
          {!expanded ? null : groups.length === 0 ? (
            <p className="px-2 py-6 text-center text-xs text-content-muted">
              {query ? 'No chats match that search.' : 'No conversations yet.'}
            </p>
          ) : (
            groups.map(([label, items]) => (
              <div key={label} className="mb-3">
                <div className="px-2 pb-1.5 pt-2 text-[10px] font-semibold uppercase tracking-wider text-content-muted/80">
                  {label}
                </div>
                <div className="space-y-0.5">
                  {items.map((s) => (
                    <SessionRow
                      key={s.session_id}
                      session={s}
                      active={s.session_id === currentSessionId}
                      onSelect={() => handleSelect(s.session_id)}
                      onRename={(title) => renameSession(s.session_id, title)}
                      onRequestDelete={() => setPendingDelete(s)}
                    />
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-subtle/8 p-3">
          {expanded ? (
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent/15 text-xs font-semibold uppercase text-accent">
                {(userName || 'J').slice(0, 1)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-medium text-content">{userName || 'User'}</div>
                <button
                  onClick={() => onOpenSettings('model')}
                  className="max-w-full truncate text-[10px] text-content-muted transition-colors hover:text-accent"
                  title={activeModel || 'No model selected'}
                >
                  {activeModel || 'No model selected'}
                </button>
              </div>
              <IconButton
                label="Settings"
                size="sm"
                tooltip="top"
                onClick={() => onOpenSettings()}
              >
                <Settings />
              </IconButton>
            </div>
          ) : (
            <IconButton
              label="Settings"
              size="md"
              tooltip="right"
              onClick={() => onOpenSettings()}
              className="mx-auto"
            >
              <Settings />
            </IconButton>
          )}
        </div>

        {/* Drag handle for resizing (docked only, expanded only) */}
        {!isDrawer && expanded && (
          <div
            onMouseDown={handleDragStart}
            className="absolute right-0 top-0 z-40 h-full w-1.5 cursor-col-resize hover:bg-accent/20 active:bg-accent/30 transition-colors"
          />
        )}
      </motion.aside>

      <Modal
        open={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        size="sm"
        title="Delete conversation?"
        description={pendingDelete?.title}
        footer={
          <>
            <Button variant="ghost" onClick={() => setPendingDelete(null)}>
              Cancel
            </Button>
            <Button variant="danger" icon={<Trash2 />} onClick={confirmDelete}>
              Delete
            </Button>
          </>
        }
      >
        <p className="text-sm leading-relaxed text-content-secondary">
          This permanently removes the transcript from disk. This cannot be undone.
        </p>
      </Modal>
    </>
  );
};

/** Mobile overlay wrapper around the same sidebar. */
export const SidebarDrawer: React.FC<{
  open: boolean;
  onClose: () => void;
  onOpenSettings: (tab?: SettingsTab) => void;
  onSelectSession?: (sid: string) => Promise<void>;
  onNewSession?: () => Promise<void>;
}> = ({ open, onClose, onOpenSettings, onSelectSession, onNewSession }) => (
  <AnimatePresence>
    {open && (
      <motion.div
        className="fixed inset-0 z-50 flex lg:hidden"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18 }}
      >
        <div className="absolute inset-0 bg-void/70 backdrop-blur-sm" onClick={onClose} aria-hidden />
        <motion.div
          className="relative h-full"
          initial={{ x: -DEFAULT_EXPANDED_WIDTH }}
          animate={{ x: 0 }}
          exit={{ x: -DEFAULT_EXPANDED_WIDTH }}
          transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
        >
          <Sidebar
            variant="drawer"
            onRequestClose={onClose}
            onOpenSettings={onOpenSettings}
            onSelectSession={onSelectSession}
            onNewSession={onNewSession}
          />
        </motion.div>
      </motion.div>
    )}
  </AnimatePresence>
);
