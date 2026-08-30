import React, { useCallback, useEffect, useState } from 'react';
import { MessageCircle, Send } from 'lucide-react';
import { ConnectorsApi } from '../../services/api';
import { ConnectorItem } from '../../types';
import { cn } from '../../utils/cn';
import { Badge, Button, Section, SkeletonRows, TextField, Toggle } from '../../components/ui';

/** Human-friendly "3h 12m" from a seconds count. */
const formatUptime = (secs: number): string => {
  if (!secs || secs <= 0) return '—';
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return `${Math.floor(secs)}s`;
};

const STATUS_TONE: Record<ConnectorItem['status'], 'success' | 'warning' | 'danger' | 'neutral'> = {
  running: 'success',
  ready: 'success',
  error: 'danger',
  disabled: 'neutral',
};

interface CardProps {
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  status?: ConnectorItem;
  tokenPlaceholder: string;
  /** Second free-text field (allowlist), label + placeholder. */
  allowLabel: string;
  allowPlaceholder: string;
  onSave: (data: { enabled: boolean; token: string; allow: string }) => Promise<string>;
}

const ConnectorCard: React.FC<CardProps> = ({
  title,
  subtitle,
  icon,
  status,
  tokenPlaceholder,
  allowLabel,
  allowPlaceholder,
  onSave,
}) => {
  const live = status?.status === 'running' || status?.status === 'ready';
  const [enabled, setEnabled] = useState(live);
  const [token, setToken] = useState('');
  const [allow, setAllow] = useState('');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  // Keep the toggle in step with server-reported status after a reload.
  useEffect(() => {
    setEnabled(live);
  }, [live]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      const message = await onSave({ enabled, token, allow });
      setToken('');
      setMsg({ ok: true, text: message });
      setTimeout(() => setMsg(null), 3000);
    } catch (err: any) {
      setMsg({ ok: false, text: err.message || 'Could not save.' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="panel space-y-4 rounded-2xl p-4"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-accent/25 bg-accent/10 text-accent [&>svg]:h-4 [&>svg]:w-4">
            {icon}
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-content">{title}</span>
              {status && (
                <Badge tone={STATUS_TONE[status.status]} dot={live}>
                  {status.status}
                </Badge>
              )}
            </div>
            <p className="mt-0.5 text-xs text-content-muted">{subtitle}</p>
          </div>
        </div>
        <Toggle checked={enabled} onChange={setEnabled} />
      </div>

      {/* Live counters — only meaningful once the bridge has run. */}
      {status && (status.messages_received > 0 || status.messages_sent > 0 || live) && (
        <div className="grid grid-cols-3 gap-2 rounded-xl border border-subtle/8 bg-surface-3/40 p-2.5 text-center">
          <div>
            <div className="text-sm font-semibold text-content">{formatUptime(status.uptime)}</div>
            <div className="text-[10px] uppercase tracking-wider text-content-muted">Uptime</div>
          </div>
          <div>
            <div className="text-sm font-semibold text-content">{status.messages_received}</div>
            <div className="text-[10px] uppercase tracking-wider text-content-muted">In</div>
          </div>
          <div>
            <div className="text-sm font-semibold text-content">{status.messages_sent}</div>
            <div className="text-[10px] uppercase tracking-wider text-content-muted">Out</div>
          </div>
        </div>
      )}

      {status?.error && (
        <div className="rounded-lg border border-danger/25 bg-danger/[0.08] px-3 py-2 text-xs text-danger">
          {status.error}
        </div>
      )}

      <div className="space-y-3 border-t border-subtle/8 pt-3">
        <TextField
          secret
          size="sm"
          label="Bot token"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder={tokenPlaceholder}
          hint="Leave blank to keep the saved token. Stored in your JARVIS config."
          autoComplete="off"
        />
        <TextField
          size="sm"
          label={allowLabel}
          value={allow}
          onChange={(e) => setAllow(e.target.value)}
          placeholder={allowPlaceholder}
          hint="Comma-separated. Blank means no one is allowed."
        />
      </div>

      <div className="flex items-center justify-between gap-3">
        <span className="min-w-0 text-xs">
          {msg && (
            <span className={cn(msg.ok ? 'text-success' : 'text-danger')}>{msg.text}</span>
          )}
        </span>
        <Button type="submit" size="sm" variant="primary" loading={saving}>
          Save {title.split(' ')[0]}
        </Button>
      </div>
    </form>
  );
};

export const ConnectorsSettings: React.FC = () => {
  const [connectors, setConnectors] = useState<ConnectorItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setConnectors(await ConnectorsApi.list());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const byName = (n: string) => connectors.find((c) => c.name.toLowerCase() === n);

  const csv = (s: string) =>
    s
      .split(',')
      .map((x) => x.trim())
      .filter(Boolean);

  if (loading) return <SkeletonRows count={4} />;

  return (
    <div className="space-y-5">
      <Section
        bare
        title="Messaging bridges"
        icon={<Send />}
        description="Talk to JARVIS from Telegram or Discord. Allowlists gate who it will answer."
      >
        <div className="space-y-3">
          <ConnectorCard
            title="Telegram"
            subtitle="Long-polling bot with per-user session routing."
            icon={<Send />}
            status={byName('telegram')}
            tokenPlaceholder="123456789:ABCdef…"
            allowLabel="Allowed usernames or IDs"
            allowPlaceholder="@you, 123456789"
            onSave={async ({ enabled, token, allow }) => {
              const res = await ConnectorsApi.configure('telegram', {
                enabled,
                bot_token: token || undefined,
                allowed_users: allow ? csv(allow) : undefined,
              });
              await load();
              return res.message;
            }}
          />

          <ConnectorCard
            title="Discord bot"
            subtitle="Guild and channel allowlists with message chunking."
            icon={<MessageCircle />}
            status={byName('discord')}
            tokenPlaceholder="MTIzNDU2…"
            allowLabel="Allowed guild / server IDs"
            allowPlaceholder="123456789012345678"
            onSave={async ({ enabled, token, allow }) => {
              const res = await ConnectorsApi.configure('discord', {
                enabled,
                bot_token: token || undefined,
                allowed_guilds: allow ? csv(allow) : undefined,
              });
              await load();
              return res.message;
            }}
          />
        </div>
      </Section>
    </div>
  );
};
