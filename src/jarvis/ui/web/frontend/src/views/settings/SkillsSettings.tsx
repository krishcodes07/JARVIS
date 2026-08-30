import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BookOpen, Layers, Loader2, Plus, Search, Trash2 } from 'lucide-react';
import { SkillsApi } from '../../services/api';
import { SkillItem } from '../../types';
import { MarkdownRenderer } from '../../utils/markdown';
import { cn } from '../../utils/cn';
import {
  Badge,
  Button,
  EmptyState,
  IconButton,
  Modal,
  SkeletonRows,
  TextField,
  Toggle,
} from '../../components/ui';

const PLACEHOLDER = `# my-skill

> One-line description shown in this list.

## When to use
Describe the situations where JARVIS should reach for this skill.

## Steps
1. …
2. …`;

/** Mirror of the backend slug rule, for the live name preview. */
const slugify = (s: string) =>
  s
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64);

/** Same fallback the API uses: front-matter `name:`, else the first heading. */
const deriveName = (content: string): string => {
  const text = content.trim();
  if (!text) return '';

  if (text.startsWith('---')) {
    const end = text.indexOf('\n---', 3);
    if (end !== -1) {
      const match = /^\s*name\s*:\s*(.+)$/m.exec(text.slice(3, end));
      if (match) {
        const slug = slugify(match[1].replace(/^["']|["']$/g, ''));
        if (slug) return slug;
      }
    }
  }

  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (trimmed.startsWith('#')) {
      const slug = slugify(trimmed.replace(/^#+/, ''));
      if (slug) return slug;
    }
  }
  return '';
};

export const SkillsSettings: React.FC = () => {
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [guide, setGuide] = useState<{ name: string; content: string } | null>(null);
  const [guideLoading, setGuideLoading] = useState<string | null>(null);

  // ─── Add-skill modal ───
  const [addOpen, setAddOpen] = useState(false);
  const [draftName, setDraftName] = useState('');
  const [draftContent, setDraftContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [addError, setAddError] = useState('');
  const [skillsDir, setSkillsDir] = useState('');

  const loadSkills = useCallback(async () => {
    setLoading(true);
    try {
      setSkills(await SkillsApi.list());
      setError('');
    } catch (e: any) {
      setError(e.message || 'Could not load skills.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSkills();
    // Purely informational — the panel still works if this 404s on an older build.
    void SkillsApi.directory()
      .then((res) => setSkillsDir(res.path))
      .catch(() => setSkillsDir(''));
  }, [loadSkills]);

  const handleToggle = async (skill: SkillItem) => {
    const next = !skill.enabled;
    setBusy(skill.name);
    // Optimistic — a failure rolls the row back below.
    setSkills((prev) => prev.map((s) => (s.name === skill.name ? { ...s, enabled: next } : s)));
    try {
      await SkillsApi.toggle(skill.name, next);
    } catch (e: any) {
      setSkills((prev) =>
        prev.map((s) => (s.name === skill.name ? { ...s, enabled: skill.enabled } : s))
      );
      setError(e.message || `Could not toggle ${skill.name}.`);
    } finally {
      setBusy(null);
    }
  };

  const openGuide = async (name: string) => {
    setGuideLoading(name);
    try {
      const res = await SkillsApi.get(name);
      setGuide({ name, content: res.content });
    } catch (e: any) {
      setError(e.message || `Could not open ${name}.`);
    } finally {
      setGuideLoading(null);
    }
  };

  const closeAdd = () => {
    setAddOpen(false);
    setAddError('');
    setDraftName('');
    setDraftContent('');
  };

  const derivedName = draftName.trim() ? slugify(draftName) : deriveName(draftContent);

  const handleCreate = async (overwrite = false) => {
    if (!draftContent.trim()) {
      setAddError('Paste the README.md content first.');
      return;
    }
    setSaving(true);
    setAddError('');
    try {
      const created = await SkillsApi.create(
        draftContent,
        draftName.trim() || undefined,
        overwrite
      );
      closeAdd();
      await loadSkills();
      setSearch(created.name);
    } catch (e: any) {
      setAddError(e.message || 'Could not create the skill.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (skill: SkillItem) => {
    if (!window.confirm(`Delete the skill "${skill.name}"? This removes its folder from disk.`)) {
      return;
    }
    setBusy(skill.name);
    try {
      await SkillsApi.remove(skill.name);
      setSkills((prev) => prev.filter((s) => s.name !== skill.name));
      setError('');
    } catch (e: any) {
      setError(e.message || `Could not delete ${skill.name}.`);
    } finally {
      setBusy(null);
    }
  };

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const list = q
      ? skills.filter(
          (s) => s.name.toLowerCase().includes(q) || s.description?.toLowerCase().includes(q)
        )
      : skills;
    // Enabled first, then alphabetical — the active set is what you scan for.
    return [...list].sort(
      (a, b) => Number(b.enabled) - Number(a.enabled) || a.name.localeCompare(b.name)
    );
  }, [skills, search]);

  const enabledCount = skills.filter((s) => s.enabled).length;

  return (
    <div className="space-y-5">
      {error && (
        <div className="rounded-xl border border-danger/25 bg-danger/[0.08] px-3.5 py-2.5 text-xs text-danger">
          {error}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Badge tone="accent">{skills.length} skills</Badge>
          {enabledCount > 0 && (
            <Badge tone="success" dot>
              {enabledCount} enabled
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="relative w-36 sm:w-52">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-content-muted" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search skills…"
              className="h-9 w-full rounded-lg border border-subtle/12 bg-surface-2 pl-8 pr-3 text-xs text-content placeholder:text-content-muted/70 outline-none transition-colors focus:border-accent/50"
            />
          </div>
          <Button
            size="sm"
            variant="primary"
            icon={<Plus className="h-3.5 w-3.5" />}
            onClick={() => setAddOpen(true)}
          >
            Add skill
          </Button>
        </div>
      </div>

      <p className="text-xs leading-relaxed text-content-muted">
        Skills are playbooks — domain knowledge and step-by-step workflows loaded into the system
        prompt on demand. Enable only what you need; each one costs context.
      </p>

      {loading ? (
        <SkeletonRows count={4} />
      ) : filtered.length === 0 ? (
        <EmptyState
          compact
          icon={<Layers />}
          title={search ? 'No matches' : 'No skills installed'}
          description={
            search
              ? 'Nothing matches that search.'
              : 'Use “Add skill” to paste a README.md, or drop a folder into your skills directory.'
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          {filtered.map((s) => (
            <div
              key={s.name}
              className={cn(
                'flex flex-col justify-between rounded-2xl border p-3.5 transition-colors',
                s.enabled
                  ? 'border-accent/25 bg-accent/[0.05]'
                  : 'border-subtle/8 bg-surface-2/40'
              )}
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <span className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <span className="font-mono text-[13px] font-semibold text-content">
                      {s.name}
                    </span>
                    {s.custom && <Badge tone="neutral">custom</Badge>}
                  </span>
                  {busy === s.name ? (
                    <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-content-muted" />
                  ) : (
                    <Toggle
                      size="sm"
                      label={`Enable ${s.name}`}
                      checked={s.enabled}
                      onChange={() => void handleToggle(s)}
                    />
                  )}
                </div>
                <p className="mt-1.5 text-xs leading-relaxed text-content-muted">{s.description}</p>
              </div>

              <div className="mt-3 flex items-center justify-between border-t border-subtle/8 pt-2.5">
                <span
                  className={cn(
                    'text-[10px] font-semibold uppercase tracking-wider',
                    s.enabled ? 'text-accent' : 'text-content-muted'
                  )}
                >
                  {s.enabled ? 'Loaded' : 'Off'}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => void openGuide(s.name)}
                    disabled={guideLoading === s.name}
                    className="inline-flex items-center gap-1 text-xs text-accent transition-colors hover:text-accent-soft disabled:opacity-50"
                  >
                    {guideLoading === s.name ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <BookOpen className="h-3.5 w-3.5" />
                    )}
                    Read
                  </button>
                  {s.custom && (
                    <IconButton
                      size="xs"
                      tone="danger"
                      label={`Delete ${s.name}`}
                      onClick={() => void handleDelete(s)}
                    >
                      <Trash2 />
                    </IconButton>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal
        open={addOpen}
        onClose={closeAdd}
        title="Add a skill"
        description="Paste the README.md content. JARVIS saves it as a skill folder and picks it up right away."
        size="lg"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={closeAdd} disabled={saving}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              loading={saving}
              disabled={!draftContent.trim()}
              onClick={() => void handleCreate(false)}
            >
              Create skill
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          {addError && (
            <div className="space-y-2 rounded-xl border border-danger/25 bg-danger/[0.08] px-3.5 py-2.5 text-xs text-danger">
              <p>{addError}</p>
              {/already exists/i.test(addError) && (
                <Button
                  size="sm"
                  variant="danger"
                  loading={saving}
                  onClick={() => void handleCreate(true)}
                >
                  Overwrite it
                </Button>
              )}
            </div>
          )}

          <TextField
            size="sm"
            label="Name (optional)"
            placeholder={derivedName || 'derived from the first heading'}
            hint={
              derivedName
                ? `Will be saved as ${derivedName}`
                : 'Leave blank to use the first “# heading” in the content.'
            }
            value={draftName}
            onChange={(e) => setDraftName(e.target.value)}
          />

          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-content-secondary">
              README.md content
            </span>
            <textarea
              value={draftContent}
              onChange={(e) => setDraftContent(e.target.value)}
              placeholder={PLACEHOLDER}
              spellCheck={false}
              rows={14}
              className="w-full resize-y rounded-xl border border-subtle/12 bg-surface-2 px-3 py-2.5 font-mono text-xs leading-relaxed text-content placeholder:text-content-muted/60 outline-none transition-colors focus:border-accent/50"
            />
          </label>

          {skillsDir && (
            <p className="text-[11px] text-content-muted">
              Saved to <span className="font-mono">{skillsDir}</span>
            </p>
          )}
        </div>
      </Modal>

      <Modal
        open={guide !== null}
        onClose={() => setGuide(null)}
        title={guide?.name}
        description="Source of the skill, exactly as JARVIS reads it."
        size="lg"
      >
        {guide && <MarkdownRenderer content={guide.content} />}
      </Modal>
    </div>
  );
};
