import React, { useEffect, useMemo, useState } from 'react';
import { ChevronRight, Search, Wrench } from 'lucide-react';
import { SystemApi } from '../../services/api';
import { ToolDefinition } from '../../types';
import { cn } from '../../utils/cn';
import { Badge, EmptyState, SkeletonRows } from '../../components/ui';

/** Prettify a snake_case category into a section heading. */
const titleCase = (s: string) =>
  s.replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const ToolRow: React.FC<{ tool: ToolDefinition }> = ({ tool }) => {
  const [open, setOpen] = useState(false);
  const params = tool.parameters || [];

  return (
    <div className="rounded-xl border border-subtle/8 bg-surface-2/40 transition-colors">
      <button
        onClick={() => params.length && setOpen((v) => !v)}
        className={cn(
          'flex w-full items-start gap-3 px-3.5 py-3 text-left',
          params.length ? 'cursor-pointer' : 'cursor-default'
        )}
      >
        {params.length > 0 && (
          <ChevronRight
            className={cn(
              'mt-0.5 h-3.5 w-3.5 shrink-0 text-content-muted transition-transform',
              open && 'rotate-90'
            )}
          />
        )}
        <span className={cn('min-w-0 flex-1', !params.length && 'pl-[1.625rem]')}>
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[13px] font-semibold text-content">{tool.name}</span>
          </span>
          {tool.description && (
            <span className="mt-1 block text-xs leading-relaxed text-content-muted">
              {tool.description}
            </span>
          )}
        </span>
      </button>

      {open && params.length > 0 && (
        <div className="border-t border-subtle/8 px-3.5 py-3 pl-[2.9rem]">
          <div className="space-y-1.5">
            {params.map((p: any, i: number) => (
              <div key={p?.name ?? i} className="flex flex-wrap items-baseline gap-x-2 text-[11px]">
                <span className="font-mono font-semibold text-content-secondary">
                  {p?.name ?? '—'}
                </span>
                {p?.type && <span className="font-mono text-content-muted">{p.type}</span>}
                {p?.required && (
                  <span className="text-[9px] font-semibold uppercase tracking-wide text-warning">
                    required
                  </span>
                )}
                {p?.description && (
                  <span className="w-full text-content-muted sm:w-auto sm:flex-1">
                    {p.description}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export const ToolsSettings: React.FC = () => {
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void SystemApi.tools()
      .then((list) => {
        if (!cancelled) setTools(list);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return tools;
    return tools.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.description?.toLowerCase().includes(q) ||
        t.category?.toLowerCase().includes(q)
    );
  }, [tools, search]);

  const grouped = useMemo(() => {
    const map = new Map<string, ToolDefinition[]>();
    for (const t of filtered) {
      const cat = t.category || 'general';
      (map.get(cat) ?? map.set(cat, []).get(cat)!).push(t);
    }
    // Sort categories alphabetically, tools by name within each.
    return Array.from(map.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([cat, list]) => [cat, list.sort((a, b) => a.name.localeCompare(b.name))] as const);
  }, [filtered]);

  if (loading) return <SkeletonRows count={6} />;

  if (failed || tools.length === 0) {
    return (
      <EmptyState
        icon={<Wrench />}
        title={failed ? 'Could not load tools' : 'No tools registered'}
        description={
          failed
            ? 'The engine did not return a tool list. It may still be starting up.'
            : 'JARVIS has no tools available in this configuration.'
        }
      />
    );
  }

  return (
    <div className="space-y-5">
      {/* Summary + search */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Badge tone="accent">{tools.length} tools</Badge>
        </div>
        <div className="relative w-44 sm:w-56">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-content-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tools…"
            className="h-9 w-full rounded-lg border border-subtle/12 bg-surface-2 pl-8 pr-3 text-xs text-content placeholder:text-content-muted/70 outline-none transition-colors focus:border-accent/50"
          />
        </div>
      </div>

      <p className="text-xs leading-relaxed text-content-muted">
        Built-in capabilities JARVIS can call during a turn. This list is read-only — enable or
        disable whole categories in your JARVIS config file.
      </p>

      {filtered.length === 0 ? (
        <EmptyState compact icon={<Search />} title="No matches" description="Nothing matches that search." />
      ) : (
        grouped.map(([category, list]) => (
          <section key={category}>
            <h3 className="mb-2 flex items-center gap-2 px-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-content-muted">
              {titleCase(category)}
              <span className="text-content-muted/60">{list.length}</span>
            </h3>
            <div className="space-y-2">
              {list.map((t) => (
                <ToolRow key={t.name} tool={t} />
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  );
};
