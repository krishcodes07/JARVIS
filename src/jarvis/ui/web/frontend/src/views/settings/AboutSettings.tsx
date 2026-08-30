import React, { useEffect, useState } from 'react';
import {
  Activity,
  Bot,
  CheckCircle2,
  Cpu,
  Database,
  ExternalLink,
  Github,
  Mic,
  Plug,
  RefreshCw,
  Scale,
  Wrench,
} from 'lucide-react';
import { SystemApi } from '../../services/api';
import { useJarvis } from '../../context/JarvisContext';
import { SystemHealth } from '../../types';
import { cn } from '../../utils/cn';
import { Badge, Button, Row, Section } from '../../components/ui';

const REPO_URL = 'https://github.com/krishcodes07/JARVIS';

/** Labels for the optional subsystems reported by /api/system/health. */
const SUBSYSTEMS: Array<{ key: string; label: string; hint: string; Icon: typeof Mic }> = [
  { key: 'voice', label: 'Voice', hint: 'Speech in and out', Icon: Mic },
  { key: 'memory', label: 'Memory', hint: 'Conversation and long-term recall', Icon: Database },
  { key: 'vector_memory', label: 'Semantic memory', hint: 'Vector store for recall', Icon: Database },
  { key: 'tools', label: 'Tools', hint: 'Built-in capabilities', Icon: Wrench },
  { key: 'mcp', label: 'MCP', hint: 'External tool servers', Icon: Plug },
];

const StatCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  tone?: 'ok' | 'warn' | 'neutral';
}> = ({ icon, label, value, tone = 'neutral' }) => (
  <div className="panel flex items-center gap-3 rounded-2xl px-4 py-3.5">
    <span
      className={cn(
        'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border [&>svg]:h-4 [&>svg]:w-4',
        tone === 'ok'
          ? 'border-success/25 bg-success/10 text-success'
          : tone === 'warn'
            ? 'border-warning/25 bg-warning/10 text-warning'
            : 'border-accent/25 bg-accent/10 text-accent'
      )}
    >
      {icon}
    </span>
    <div className="min-w-0">
      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-content-muted">
        {label}
      </div>
      <div className="mt-0.5 truncate text-sm font-semibold text-content">{value}</div>
    </div>
  </div>
);

export const AboutSettings: React.FC = () => {
  const { connectionState } = useJarvis();
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      setHealth(await SystemApi.health());
    } catch {
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const engineOk = !!health?.engine_initialized;
  const connectors = health?.connectors ?? [];
  const activeConnectors = connectors.filter(
    (c) => c.status === 'running' || c.status === 'ready'
  );
  const subsystems = health?.subsystems;

  return (
    <div className="space-y-7">
      {/* Identity */}
      <div className="panel flex items-center gap-4 rounded-2xl px-5 py-5">
        <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-accent/25 bg-accent/12 text-accent">
          <Bot className="h-7 w-7" />
        </span>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-display text-lg font-bold text-content">JARVIS</h2>
            {health?.version && <Badge tone="accent">v{health.version}</Badge>}
          </div>
          <p className="mt-1 text-xs leading-relaxed text-content-muted">
            A multi-provider, tool-calling, MCP-powered assistant with a voice, memory, and a
            desktop it can drive.
          </p>
        </div>
      </div>

      {/* Live status */}
      <Section
        bare
        title="System status"
        icon={<Activity />}
        actions={
          <Button
            size="sm"
            variant="ghost"
            icon={<RefreshCw className={cn(loading && 'animate-spin')} />}
            onClick={() => void refresh()}
            disabled={loading}
          >
            Refresh
          </Button>
        }
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <StatCard
            icon={engineOk ? <CheckCircle2 /> : <Cpu />}
            label="Engine"
            tone={engineOk ? 'ok' : 'warn'}
            value={loading ? 'Checking…' : engineOk ? 'Initialised' : 'Degraded'}
          />
          <StatCard
            icon={<Activity />}
            label="Realtime link"
            tone={connectionState === 'open' ? 'ok' : 'warn'}
            value={
              connectionState === 'open'
                ? 'Connected'
                : connectionState === 'connecting'
                  ? 'Connecting…'
                  : 'Offline'
            }
          />
          <StatCard
            icon={<Bot />}
            label="Active model"
            value={loading ? '…' : health?.active_model || 'None'}
          />
          <StatCard
            icon={<Plug />}
            label="Connectors"
            tone={activeConnectors.length ? 'ok' : 'neutral'}
            value={
              loading
                ? '…'
                : activeConnectors.length
                  ? `${activeConnectors.length} of ${connectors.length} active`
                  : 'None active'
            }
          />
        </div>
      </Section>

      {/* Subsystems */}
      {subsystems && (
        <Section
          title="Subsystems"
          icon={<Cpu />}
          description="Optional components, and whether they came up on this run."
        >
          {SUBSYSTEMS.filter((s) => s.key in subsystems).map(({ key, label, hint, Icon }) => (
            <Row
              key={key}
              label={label}
              description={hint}
              icon={<Icon />}
              control={
                <Badge tone={subsystems[key] ? 'success' : 'neutral'}>
                  {subsystems[key] ? 'available' : 'off'}
                </Badge>
              }
            />
          ))}
        </Section>
      )}

      {/* Connector detail */}
      {connectors.length > 0 && (
        <Section title="Connectors" icon={<Plug />}>
          {connectors.map((c) => {
            const up = c.status === 'running' || c.status === 'ready';
            return (
              <Row
                key={c.name}
                label={<span className="capitalize">{c.name}</span>}
                description={c.error || undefined}
                icon={
                  <span
                    className={cn(
                      'block h-2 w-2 rounded-full',
                      up ? 'bg-success' : c.status === 'error' ? 'bg-danger' : 'bg-content-muted/40'
                    )}
                  />
                }
                control={
                  <Badge tone={up ? 'success' : c.status === 'error' ? 'danger' : 'neutral'}>
                    {c.status}
                  </Badge>
                }
              />
            );
          })}
        </Section>
      )}

      {/* Links */}
      <Section title="Project" icon={<Github />}>
        <Row
          label="Source & issues"
          icon={<Github />}
          description="Browse the code or report a bug."
          control={
            <a
              href={REPO_URL}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1 text-xs text-accent hover:text-accent-soft"
            >
              GitHub
              <ExternalLink className="h-3 w-3" />
            </a>
          }
        />
        <Row
          label="License"
          icon={<Scale />}
          description="Released under the MIT License."
          control={<Badge tone="neutral">MIT</Badge>}
        />
      </Section>
    </div>
  );
};
