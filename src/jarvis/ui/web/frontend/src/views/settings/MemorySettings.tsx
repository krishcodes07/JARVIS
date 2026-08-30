import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Brain,
  Database,
  History,
  ScrollText,
  Shield,
  Trash2,
} from 'lucide-react';
import { ConfigApi, SystemApi } from '../../services/api';
import { cn } from '../../utils/cn';
import {
  Badge,
  Button,
  Modal,
  Row,
  Section,
  Select,
  SkeletonRows,
  Toggle,
} from '../../components/ui';

/** Local mirror of the `memory` + `tools` keys this panel edits. */
interface MemoryDraft {
  conversation: { max_messages: number; auto_summarize: boolean; summarize_after: number };
  long_term: { enabled: boolean; auto_extract: boolean };
  vector: { enabled: boolean; embedding_backend: string };
  autoApprove: boolean;
}

const DEFAULT_DRAFT: MemoryDraft = {
  conversation: { max_messages: 100, auto_summarize: true, summarize_after: 50 },
  long_term: { enabled: true, auto_extract: true },
  vector: { enabled: true, embedding_backend: 'auto' },
  autoApprove: true,
};

const EMBEDDING_BACKENDS = [
  { value: 'auto', label: 'Auto — provider, then local fallback' },
  { value: 'local', label: 'Local — bundled model, no API key' },
  { value: 'provider', label: 'Provider — fail rather than degrade' },
];

/** Small numeric stepper; the native spinner is too wide for a settings row. */
const NumberBox: React.FC<{
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label: string;
}> = ({ value, onChange, min, max, step = 1, label }) => (
  <input
    type="number"
    aria-label={label}
    value={value}
    min={min}
    max={max}
    step={step}
    onChange={(e) => onChange(Number(e.target.value) || 0)}
    className="h-9 w-20 rounded-lg border border-subtle/15 bg-surface-2 px-2 text-center font-mono text-xs text-content outline-none transition-colors focus:border-accent/50"
  />
);

export const MemorySettings: React.FC = () => {
  const [draft, setDraft] = useState<MemoryDraft>(DEFAULT_DRAFT);
  const [baseline, setBaseline] = useState<MemoryDraft>(DEFAULT_DRAFT);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [purging, setPurging] = useState(false);
  const [purgeOpen, setPurgeOpen] = useState(false);
  const [status, setStatus] = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    void ConfigApi.get()
      .then((cfg) => {
        if (cancelled || !cfg) return;
        const m = cfg.memory || {};
        const next: MemoryDraft = {
          conversation: {
            max_messages: m.conversation?.max_messages ?? DEFAULT_DRAFT.conversation.max_messages,
            auto_summarize: m.conversation?.auto_summarize ?? true,
            summarize_after: m.conversation?.summarize_after ?? DEFAULT_DRAFT.conversation.summarize_after,
          },
          long_term: {
            enabled: m.long_term?.enabled ?? true,
            auto_extract: m.long_term?.auto_extract ?? true,
          },
          vector: {
            enabled: m.vector?.enabled ?? true,
            embedding_backend: m.vector?.embedding_backend || 'auto',
          },
          autoApprove: cfg.tools?.auto_approve ?? true,
        };
        setDraft(next);
        setBaseline(next);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const patch = useCallback(<K extends keyof MemoryDraft>(key: K, value: MemoryDraft[K]) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
    setStatus(null);
  }, []);

  const dirty = JSON.stringify(draft) !== JSON.stringify(baseline);

  const handleSave = async () => {
    setSaving(true);
    setStatus(null);
    try {
      // `tools` and `memory` are separate top-level sections; the deep merge
      // keeps every sibling key in each of them intact.
      const res = await ConfigApi.update({
        memory: {
          conversation: draft.conversation,
          long_term: draft.long_term,
          vector: draft.vector,
        },
        tools: { auto_approve: draft.autoApprove },
      });
      setBaseline(draft);
      setStatus(
        res.rejected?.length
          ? { ok: false, message: `Saved, but these keys were rejected: ${res.rejected.join(', ')}` }
          : { ok: true, message: 'Memory and safety settings saved.' }
      );
    } catch (e: any) {
      setStatus({ ok: false, message: e.message || 'Could not save settings.' });
    } finally {
      setSaving(false);
    }
  };

  const handlePurge = async () => {
    setPurging(true);
    try {
      const res = await SystemApi.clearMemory();
      setStatus({ ok: res.status !== 'error', message: res.message });
    } catch (e: any) {
      setStatus({ ok: false, message: e.message || 'Purge failed.' });
    } finally {
      setPurging(false);
      setPurgeOpen(false);
    }
  };

  if (loading) return <SkeletonRows count={6} />;

  return (
    <div className="space-y-7">
      <Section
        title="Conversation window"
        icon={<History />}
        description="Short-term memory: what JARVIS carries forward inside a single session."
      >
        <Row
          label="Messages kept in context"
          icon={<ScrollText />}
          description="Older turns drop out of the prompt once this many messages accumulate."
          control={
            <NumberBox
              label="Messages kept in context"
              value={draft.conversation.max_messages}
              min={10}
              max={500}
              step={10}
              onChange={(v) => patch('conversation', { ...draft.conversation, max_messages: v })}
            />
          }
        />
        <Row
          label="Summarise older turns"
          description="Instead of dropping them outright, condense them into a running summary."
          control={
            <Toggle
              checked={draft.conversation.auto_summarize}
              onChange={(v) => patch('conversation', { ...draft.conversation, auto_summarize: v })}
            />
          }
        />
        {draft.conversation.auto_summarize && (
          <Row
            label="Summarise after"
            description="Message count that triggers a summarisation pass."
            control={
              <NumberBox
                label="Summarise after"
                value={draft.conversation.summarize_after}
                min={5}
                max={draft.conversation.max_messages}
                step={5}
                onChange={(v) =>
                  patch('conversation', { ...draft.conversation, summarize_after: v })
                }
              />
            }
          />
        )}
      </Section>

      <Section
        title="Long-term memory"
        icon={<Brain />}
        description="Facts JARVIS remembers about you across sessions."
      >
        <Row
          label="Enable long-term memory"
          control={
            <Toggle
              checked={draft.long_term.enabled}
              onChange={(v) => patch('long_term', { ...draft.long_term, enabled: v })}
            />
          }
        />
        <Row
          label="Extract facts automatically"
          description="Pull durable details out of conversations without being asked. Costs an extra model call per turn."
          control={
            <Toggle
              disabled={!draft.long_term.enabled}
              checked={draft.long_term.auto_extract}
              onChange={(v) => patch('long_term', { ...draft.long_term, auto_extract: v })}
            />
          }
        />
      </Section>

      <Section
        title="Semantic search"
        icon={<Database />}
        description="Vector store used to recall relevant past context."
      >
        <Row
          label="Enable vector memory"
          control={
            <Toggle
              checked={draft.vector.enabled}
              onChange={(v) => patch('vector', { ...draft.vector, enabled: v })}
            />
          }
        />
        <Row
          stacked
          label="Embeddings"
          description="Local embeddings need no API key and never leave this machine."
          control={
            <Select
              size="sm"
              options={EMBEDDING_BACKENDS}
              value={draft.vector.embedding_backend}
              disabled={!draft.vector.enabled}
              onChange={(e) => patch('vector', { ...draft.vector, embedding_backend: e.target.value })}
            />
          }
        />
        <Row
          label="Purge stored embeddings"
          description="Deletes everything under ~/.jarvis/workspace/vector_store. Conversation history is untouched."
          control={
            <Button
              size="sm"
              variant="danger"
              icon={<Trash2 />}
              loading={purging}
              onClick={() => setPurgeOpen(true)}
            >
              Purge
            </Button>
          }
        />
      </Section>

      <Section title="Safety" icon={<Shield />} description="Guardrails on tool execution.">
        <Row
          label="Auto-approve tool calls"
          icon={<Shield />}
          description="When off, JARVIS pauses for confirmation before running anything marked dangerous — shell commands, file writes, desktop automation."
          control={
            <Toggle checked={draft.autoApprove} onChange={(v) => patch('autoApprove', v)} />
          }
        />
        {draft.autoApprove && (
          <Row
            label={
              <span className="flex items-center gap-2">
                <AlertTriangle className="h-3.5 w-3.5 text-warning" />
                Destructive actions run unattended
              </span>
            }
            description="JARVIS can delete files, run shell commands, and drive the desktop without asking. Leave this on only on a machine you're happy to let it change."
          />
        )}
        <Row
          label="Emergency stop"
          description={
            <>
              Press{' '}
              <kbd className="rounded border border-subtle/20 bg-surface-3 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-accent">
                Ctrl+Alt+Q
              </kbd>{' '}
              at any time to abort desktop automation.
            </>
          }
        />
      </Section>

      {/* ─── Save bar ─── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 text-xs">
          {status ? (
            <span className={cn(status.ok ? 'text-success' : 'text-danger')}>{status.message}</span>
          ) : dirty ? (
            <Badge tone="warning" dot>
              Unsaved changes
            </Badge>
          ) : (
            <span className="text-content-muted">Saved to your JARVIS config.</span>
          )}
        </div>
        <Button
          variant="primary"
          size="sm"
          loading={saving}
          disabled={!dirty}
          onClick={() => void handleSave()}
        >
          Save changes
        </Button>
      </div>

      <Modal
        open={purgeOpen}
        onClose={() => setPurgeOpen(false)}
        size="sm"
        title="Purge vector memory?"
        description="Every embedded memory is deleted. This cannot be undone, and JARVIS will lose recall of anything it learned semantically."
        footer={
          <>
            <Button size="sm" variant="ghost" onClick={() => setPurgeOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              variant="danger"
              icon={<Trash2 />}
              loading={purging}
              onClick={() => void handlePurge()}
            >
              Purge everything
            </Button>
          </>
        }
      >
        <p className="text-xs leading-relaxed text-content-secondary">
          Your saved chat sessions and the facts in long-term memory stay where they are — only the
          semantic index is cleared.
        </p>
      </Modal>
    </div>
  );
};
