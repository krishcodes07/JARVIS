import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Bot, Brain, Check, ExternalLink, Key, Search } from 'lucide-react';
import { useJarvis } from '../../context/JarvisContext';
import { ConfigApi } from '../../services/api';
import { EffortInfo, ModelItem, ProviderItem } from '../../types';
import { cn } from '../../utils/cn';
import {
  Badge,
  Button,
  EmptyState,
  Modal,
  Row,
  Section,
  SkeletonRows,
  TextField,
} from '../../components/ui';

/** Last-resort ladder, used only when neither the model nor the backend reports one. */
const FALLBACK_EFFORTS = ['none', 'low', 'medium', 'high'];

const formatTokens = (n?: number): string | null => {
  if (!n || n <= 0) return null;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n % 1_000_000 === 0 ? 0 : 1)}M`;
  if (n >= 1000) return `${Math.round(n / 1000)}K`;
  return String(n);
};

export const ModelSettings: React.FC = () => {
  const {
    activeModel,
    activeProvider,
    reasoningEffort,
    updateActiveModel,
    setReasoningEffort,
  } = useJarvis();

  const [providers, setProviders] = useState<ProviderItem[]>([]);
  const [selectedProvider, setSelectedProvider] = useState(activeProvider || 'openai');
  const [models, setModels] = useState<ModelItem[]>([]);
  const [search, setSearch] = useState('');
  const [providerSearch, setProviderSearch] = useState('');
  const [loadingModels, setLoadingModels] = useState(true);
  const [switching, setSwitching] = useState<string | null>(null);
  const [effortInfo, setEffortInfo] = useState<EffortInfo | null>(null);
  const [error, setError] = useState('');

  const [connectOpen, setConnectOpen] = useState(false);
  const [connectProviderId, setConnectProviderId] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [connecting, setConnecting] = useState(false);
  const [connectResult, setConnectResult] = useState<{ ok: boolean; message: string } | null>(null);

  const loadProviders = useCallback(async () => {
    try {
      setProviders(await ConfigApi.listProviders());
    } catch (e: any) {
      setError(e.message || 'Could not load providers.');
    }
  }, []);

  useEffect(() => {
    void loadProviders();
    // The backend knows the true effort ladder for the *active* model; it is the
    // fallback when the catalogue entry doesn't declare one.
    ConfigApi.getEffort()
      .then(setEffortInfo)
      .catch(() => setEffortInfo(null));
  }, [loadProviders]);

  useEffect(() => {
    if (activeProvider) setSelectedProvider(activeProvider);
  }, [activeProvider]);

  useEffect(() => {
    if (!selectedProvider) return;
    let cancelled = false;
    setLoadingModels(true);
    ConfigApi.listModels(selectedProvider)
      .then((list) => {
        if (!cancelled) setModels(list);
      })
      .catch(() => {
        if (!cancelled) setModels([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingModels(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedProvider]);

  const activeProviderMeta = providers.find((p) => p.id === selectedProvider);
  const activeModelMeta = models.find((m) => m.id === activeModel);

  // Prefer the catalogue's per-model ladder, then the backend's, then the default.
  const efforts = useMemo(() => {
    if (activeModelMeta?.available_efforts?.length) return activeModelMeta.available_efforts;
    if (effortInfo?.available?.length) return effortInfo.available;
    return FALLBACK_EFFORTS;
  }, [activeModelMeta, effortInfo]);

  // Only disable once we actually know the model doesn't reason — an unknown
  // model shouldn't lock the control.
  const effortSupported = activeModelMeta
    ? activeModelMeta.has_reasoning
    : effortInfo
      ? effortInfo.supported
      : true;

  const handleSelectModel = async (modelId: string) => {
    setSwitching(modelId);
    setError('');
    try {
      await updateActiveModel(selectedProvider, modelId);
      await loadProviders();
      const fresh = await ConfigApi.getEffort().catch(() => null);
      if (fresh) setEffortInfo(fresh);
    } catch (e: any) {
      setError(e.message || 'Could not switch model.');
    } finally {
      setSwitching(null);
    }
  };

  const handleEffortChange = async (next: string) => {
    setError('');
    try {
      // A single POST /config/effort — switching the provider again just to
      // change effort would needlessly tear down the client.
      await setReasoningEffort(next);
      setEffortInfo((prev) => (prev ? { ...prev, current: next } : prev));
    } catch (e: any) {
      setError(e.message || 'Could not change reasoning effort.');
    }
  };

  /** Open the connect dialog for a specific provider. */
  const openConnectDialog = useCallback((providerId: string) => {
    setConnectProviderId(providerId);
    setConnectOpen(true);
    setFormValues({});
    setConnectResult(null);
  }, []);

  const currentConnectMeta = providers.find((p) => p.id === connectProviderId) || activeProviderMeta;
  const connectFields = useMemo(() => {
    if (currentConnectMeta?.fields && currentConnectMeta.fields.length > 0) {
      return currentConnectMeta.fields;
    }
    if (currentConnectMeta?.env_vars && currentConnectMeta.env_vars.length > 0) {
      return currentConnectMeta.env_vars.map((ev) => ({
        name: ev,
        label: ev.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' '),
        is_secret: ['KEY', 'SECRET', 'TOKEN', 'PASSWORD', 'CREDENTIAL', 'AUTH'].some((k) => ev.toUpperCase().includes(k)),
      }));
    }
    return [{ name: `${(connectProviderId || selectedProvider || 'API').toUpperCase()}_API_KEY`, label: 'API Key', is_secret: true }];
  }, [currentConnectMeta, connectProviderId, selectedProvider]);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    const targetProvider = connectProviderId || selectedProvider;
    setConnecting(true);
    setConnectResult(null);
    try {
      const res = await ConfigApi.connectProvider(
        targetProvider,
        formValues
      );
      setConnectResult({
        ok: true,
        message: res.message || 'Connected successfully.',
      });
      setFormValues({});
      await loadProviders();
      // After connecting, select this provider
      setSelectedProvider(targetProvider);
    } catch (err: any) {
      setConnectResult({ ok: false, message: err.message || 'Could not save credentials.' });
    } finally {
      setConnecting(false);
    }
  };

  const filtered = models.filter((m) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    return m.name.toLowerCase().includes(q) || m.id.toLowerCase().includes(q);
  });

  return (
    <div className="space-y-7">
      {error && (
        <div className="rounded-xl border border-danger/25 bg-danger/[0.08] px-3.5 py-2.5 text-xs text-danger">
          {error}
        </div>
      )}

      {/* ─── Active model summary ─── */}
      <div className="panel flex flex-wrap items-center justify-between gap-4 rounded-2xl px-4 py-3.5">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-accent/25 bg-accent/12 text-accent">
            <Bot className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-content-muted">
              Active model
            </div>
            <div className="truncate font-mono text-sm font-semibold text-content">
              {activeModel || 'None selected'}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="accent">{activeProviderMeta?.name || activeProvider || 'unknown'}</Badge>
          {reasoningEffort && reasoningEffort !== 'none' && (
            <Badge tone="info" icon={<Brain />}>
              {reasoningEffort}
            </Badge>
          )}
          {formatTokens(activeModelMeta?.context_window) && (
            <Badge tone="neutral">{formatTokens(activeModelMeta?.context_window)} context</Badge>
          )}
        </div>
      </div>

      {/* ─── Providers ─── */}
      <Section
        bare
        title="Provider"
        description="Pick the service that runs your models. A filled dot means JARVIS found credentials for it."
        actions={
          <div className="flex items-center gap-2">
            <div className="relative w-36 sm:w-44">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-content-muted" />
              <input
                value={providerSearch}
                onChange={(e) => setProviderSearch(e.target.value)}
                placeholder="Filter providers…"
                className="h-9 w-full rounded-lg border border-subtle/12 bg-surface-2 pl-8 pr-3 text-xs text-content placeholder:text-content-muted/70 outline-none transition-colors focus:border-accent/50"
              />
            </div>
            <Button size="sm" variant="outline" icon={<Key />} onClick={() => openConnectDialog(selectedProvider)}>
              Connect key
            </Button>
          </div>
        }
      >
        <div className="scroll-area flex max-h-[14rem] flex-wrap gap-2 overflow-y-auto">
          {providers.length === 0 ? (
            <SkeletonRows count={1} className="w-full" />
          ) : (
            [...providers]
              .filter((p) => {
                const q = providerSearch.trim().toLowerCase();
                if (!q) return true;
                return p.name.toLowerCase().includes(q) || p.id.toLowerCase().includes(q);
              })
              .sort((a, b) => {
                // Connected providers come first
                if (a.connected && !b.connected) return -1;
                if (!a.connected && b.connected) return 1;
                return 0;
              })
              .map((p) => {
                const selected = p.id === selectedProvider;
                return (
                  <button
                    key={p.id}
                    onClick={() => {
                      if (!p.connected) {
                        // Open connect dialog for unconnected providers
                        openConnectDialog(p.id);
                      } else {
                        setSelectedProvider(p.id);
                      }
                    }}
                    className={cn(
                      'flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-medium transition-all',
                      selected
                        ? 'border-accent/40 bg-accent/12 text-content'
                        : p.connected
                          ? 'border-subtle/10 bg-surface-2/50 text-content-secondary hover:border-accent/25 hover:text-content'
                          : 'border-subtle/10 bg-surface-2/30 text-content-muted/70 hover:border-accent/25 hover:text-content-secondary'
                    )}
                  >
                    <span
                      className={cn(
                        'h-1.5 w-1.5 shrink-0 rounded-full',
                        p.connected ? 'bg-success' : 'bg-content-muted/40'
                      )}
                    />
                    <span>{p.name}</span>
                    {p.model_count > 1 && (
                      <span className="text-[10px] text-content-muted">{p.model_count}</span>
                    )}
                    {!p.connected && (
                      <Key className="h-3 w-3 text-content-muted/50" />
                    )}
                  </button>
                );
              })
          )}
        </div>
      </Section>

      {/* ─── Reasoning effort ─── */}
      <Section
        title="Reasoning effort"
        icon={<Brain />}
        description={
          effortSupported
            ? 'How much thinking budget the model spends before answering.'
            : `${activeModel || 'This model'} does not expose a configurable thinking budget.`
        }
      >
        <Row
          stacked
          label="Effort level"
          description={
            effortSupported
              ? 'Higher settings trade latency and tokens for better reasoning.'
              : 'Pick a reasoning model to enable this.'
          }
          control={
            <div
              role="radiogroup"
              aria-label="Reasoning effort"
              className={cn(
                'grid gap-1 rounded-xl border border-subtle/10 bg-surface-3/60 p-1',
                !effortSupported && 'pointer-events-none opacity-45'
              )}
              style={{ gridTemplateColumns: `repeat(${efforts.length}, minmax(0, 1fr))` }}
            >
              {efforts.map((level) => {
                const selected = (reasoningEffort || 'none').toLowerCase() === level.toLowerCase();
                return (
                  <button
                    key={level}
                    role="radio"
                    aria-checked={selected}
                    disabled={!effortSupported}
                    onClick={() => void handleEffortChange(level)}
                    className={cn(
                      'rounded-lg py-1.5 font-mono text-[11px] uppercase tracking-wider transition-all',
                      selected
                        ? 'bg-accent/20 font-bold text-accent-soft shadow-accent-sm'
                        : 'text-content-muted hover:text-content-secondary'
                    )}
                  >
                    {level}
                  </button>
                );
              })}
            </div>
          }
        />
      </Section>

      {/* ─── Model catalogue ─── */}
      <Section
        bare
        title={`Models${filtered.length ? ` · ${filtered.length}` : ''}`}
        description={`Available from ${activeProviderMeta?.name || selectedProvider}.`}
        actions={
          <div className="relative w-40 sm:w-52">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-content-muted" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter models…"
              className="h-9 w-full rounded-lg border border-subtle/12 bg-surface-2 pl-8 pr-3 text-xs text-content placeholder:text-content-muted/70 outline-none transition-colors focus:border-accent/50"
            />
          </div>
        }
      >
        {loadingModels ? (
          <SkeletonRows count={4} />
        ) : filtered.length === 0 ? (
          <EmptyState
            compact
            icon={<Bot />}
            title="No models found"
            description={
              search
                ? 'Nothing matches that filter.'
                : `The models.dev catalogue has no entries for ${selectedProvider}.`
            }
          />
        ) : (
          <div className="scroll-area grid max-h-[22rem] grid-cols-1 gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
            {filtered.map((m) => {
              const selected = activeModel === m.id;
              const ctx = formatTokens(m.context_window);
              const out = formatTokens(m.max_tokens);
              return (
                <button
                  key={m.id}
                  onClick={() => void handleSelectModel(m.id)}
                  disabled={switching !== null}
                  className={cn(
                    'flex items-start justify-between gap-2 rounded-xl border p-3 text-left transition-all',
                    'disabled:opacity-60',
                    selected
                      ? 'border-accent/40 bg-accent/12'
                      : 'border-subtle/8 bg-surface-2/40 hover:border-accent/25 hover:bg-surface-2/70'
                  )}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-[13px] font-semibold text-content">
                      {m.name}
                    </span>
                    <span className="mt-0.5 block truncate font-mono text-[10px] text-content-muted">
                      {m.id}
                    </span>
                    <span className="mt-1.5 flex flex-wrap items-center gap-1">
                      {m.has_reasoning && (
                        <Badge tone="info" className="!px-1.5 !text-[9px]">
                          reasoning
                        </Badge>
                      )}
                      {ctx && (
                        <Badge tone="neutral" className="!px-1.5 !text-[9px]">
                          {ctx} in
                        </Badge>
                      )}
                      {out && (
                        <Badge tone="neutral" className="!px-1.5 !text-[9px]">
                          {out} out
                        </Badge>
                      )}
                    </span>
                  </span>
                  {selected && <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent" />}
                </button>
              );
            })}
          </div>
        )}
      </Section>

      {/* ─── Connect modal ─── */}
      <Modal
        open={connectOpen}
        onClose={() => {
          setConnectOpen(false);
          setConnectResult(null);
        }}
        title={`Connect ${currentConnectMeta?.name || connectProviderId || selectedProvider}`}
        description="Credentials are saved to ~/.jarvis/.env and exported into the process."
        size="sm"
      >
        <form onSubmit={handleConnect} className="space-y-4">
          {connectFields.map((f) => (
            <TextField
              key={f.name}
              secret={f.is_secret}
              label={f.label}
              value={formValues[f.name] || ''}
              onChange={(e) =>
                setFormValues((prev) => ({ ...prev, [f.name]: e.target.value }))
              }
              placeholder={f.is_secret ? 'Enter key…' : `Enter ${f.label.toLowerCase()}…`}
              autoComplete="off"
            />
          ))}

          {currentConnectMeta?.doc_url && (
            <a
              href={currentConnectMeta.doc_url}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1 text-xs text-accent hover:text-accent-soft"
            >
              Where do I find my credentials?
              <ExternalLink className="h-3 w-3" />
            </a>
          )}

          {connectResult && (
            <div
              className={cn(
                'rounded-xl border px-3 py-2 text-xs',
                connectResult.ok
                  ? 'border-success/25 bg-success/[0.08] text-success'
                  : 'border-danger/25 bg-danger/[0.08] text-danger'
              )}
            >
              {connectResult.message}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-1">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => {
                setConnectOpen(false);
                setConnectResult(null);
              }}
            >
              Close
            </Button>
            <Button
              type="submit"
              size="sm"
              variant="primary"
              loading={connecting}
              disabled={connectFields.some((f) => !formValues[f.name]?.trim())}
            >
              Save credentials
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
