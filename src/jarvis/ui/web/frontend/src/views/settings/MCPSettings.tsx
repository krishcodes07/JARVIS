import React, { useCallback, useEffect, useState } from 'react';
import { Globe, Loader2, Plug, Plus, Trash2, Wrench } from 'lucide-react';
import { MCPApi } from '../../services/api';
import { MCPServerItem } from '../../types';
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
  Toggle,
} from '../../components/ui';

/**
 * Split a command-line argument string, honouring single and double quotes so
 * that `-c "print('hi')"` stays one argument. The old code did a bare
 * `split(' ')`, which shattered any quoted path or snippet.
 */
export const tokenizeArgs = (input: string): string[] => {
  const tokens: string[] = [];
  const re = /"([^"]*)"|'([^']*)'|(\S+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(input)) !== null) {
    tokens.push(m[1] ?? m[2] ?? m[3] ?? '');
  }
  return tokens;
};

export const MCPSettings: React.FC = () => {
  const [servers, setServers] = useState<MCPServerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [oauthStatus, setOauthStatus] = useState('');

  const [addOpen, setAddOpen] = useState(false);
  const [name, setName] = useState('');
  const [command, setCommand] = useState('');
  const [argsStr, setArgsStr] = useState('');
  const [adding, setAdding] = useState(false);
  const [addMsg, setAddMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  const loadServers = useCallback(async () => {
    setLoading(true);
    try {
      setServers(await MCPApi.listServers());
      setError('');
    } catch (e: any) {
      setError(e.message || 'Could not load MCP servers.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadServers();
  }, [loadServers]);

  const handleToggle = async (server: MCPServerItem) => {
    const next = !server.enabled;
    setBusy(server.name);
    setError('');
    try {
      const res = await MCPApi.toggleServer(server.name, next);
      // A failed connect comes back 200 with connected=false and a reason —
      // without this the toggle just springs back with no explanation.
      if (next && !res.connected) {
        setError(res.message || `Could not connect ${server.name}.`);
      }
      await loadServers();
    } catch (e: any) {
      setError(e.message || `Could not toggle ${server.name}.`);
    } finally {
      setBusy(null);
    }
  };

  const handleDelete = async (serverName: string) => {
    setBusy(serverName);
    try {
      await MCPApi.deleteServer(serverName);
      await loadServers();
    } catch (e: any) {
      setError(e.message || `Could not remove ${serverName}.`);
    } finally {
      setBusy(null);
      setPendingDelete(null);
    }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdding(true);
    setAddMsg(null);
    try {
      const res = await MCPApi.addServer({
        name: name.trim().toLowerCase(),
        command: command.trim(),
        args: tokenizeArgs(argsStr.trim()),
        env: {},
      });
      setAddMsg({ ok: true, text: res.message || 'Server added.' });
      setName('');
      setCommand('');
      setArgsStr('');
      await loadServers();
      setTimeout(() => {
        setAddOpen(false);
        setAddMsg(null);
      }, 900);
    } catch (err: any) {
      setAddMsg({ ok: false, text: err.message || 'Could not add server.' });
    } finally {
      setAdding(false);
    }
  };

  const handleGoogleOAuth = async () => {
    setOauthStatus('Opening browser for Google sign-in…');
    try {
      const res = await MCPApi.googleOAuth();
      setOauthStatus(`Signed in as ${res.email}.`);
      await loadServers();
      setTimeout(() => setOauthStatus(''), 4000);
    } catch (err: any) {
      setOauthStatus(`Sign-in failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-xl border border-danger/25 bg-danger/[0.08] px-3.5 py-2.5 text-xs text-danger">
          {error}
        </div>
      )}

      <Section
        bare
        title={`Servers${servers.length ? ` · ${servers.length}` : ''}`}
        icon={<Plug />}
        description="Model Context Protocol servers expose external tools — sandboxes, Google services, databases, and APIs — to JARVIS."
        actions={
          <div className="flex items-center gap-2">
            <Button size="sm" variant="ghost" icon={<Globe />} onClick={() => void handleGoogleOAuth()}>
              Google
            </Button>
            <Button size="sm" variant="outline" icon={<Plus />} onClick={() => setAddOpen(true)}>
              Add server
            </Button>
          </div>
        }
      >
        {oauthStatus && (
          <div className="mb-3 rounded-xl border border-accent/25 bg-accent/[0.08] px-3.5 py-2.5 text-xs text-accent-soft">
            {oauthStatus}
          </div>
        )}

        {loading ? (
          <SkeletonRows count={3} />
        ) : servers.length === 0 ? (
          <EmptyState
            compact
            icon={<Plug />}
            title="No MCP servers"
            description="Add one to give JARVIS extra tools."
          />
        ) : (
          <div className="space-y-2">
            {servers.map((s) => (
              <div
                key={s.name}
                className={cn(
                  'rounded-xl border p-3.5 transition-colors',
                  s.enabled
                    ? 'border-subtle/10 bg-surface-2/50'
                    : 'border-subtle/8 bg-surface-2/25 opacity-70'
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <span
                      className={cn(
                        'mt-1 block h-2 w-2 shrink-0 rounded-full',
                        s.connected ? 'bg-success' : 'bg-content-muted/40'
                      )}
                      title={s.connected ? 'Connected' : 'Not connected'}
                    />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-[13px] font-semibold text-content">
                          {s.name}
                        </span>
                        {s.category && (
                          <Badge tone="neutral" className="!px-1.5 !text-[9px]">
                            {s.category}
                          </Badge>
                        )}
                        {s.tool_count > 0 && (
                          <Badge tone="accent" icon={<Wrench />} className="!px-1.5 !text-[9px]">
                            {s.tool_count}
                          </Badge>
                        )}
                        {s.requires_oauth && (
                          <Badge tone="warning" className="!px-1.5 !text-[9px]">
                            oauth
                          </Badge>
                        )}
                      </div>
                      {s.description && (
                        <p className="mt-1 text-xs leading-relaxed text-content-muted">
                          {s.description}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-2">
                    {busy === s.name ? (
                      <Loader2 className="h-4 w-4 animate-spin text-content-muted" />
                    ) : (
                      <Toggle
                        size="sm"
                        label={`Enable ${s.name}`}
                        checked={s.enabled}
                        onChange={() => void handleToggle(s)}
                      />
                    )}
                    {s.custom && (
                      <button
                        onClick={() => setPendingDelete(s.name)}
                        aria-label={`Remove ${s.name}`}
                        className="rounded-lg p-1.5 text-content-muted transition-colors hover:bg-danger/10 hover:text-danger"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Add-server modal */}
      <Modal
        open={addOpen}
        onClose={() => {
          setAddOpen(false);
          setAddMsg(null);
        }}
        title="Add MCP server"
        description="Runs a stdio MCP server as a subprocess. Arguments accept quotes for paths with spaces."
        size="sm"
      >
        <form onSubmit={handleAdd} className="space-y-4">
          <TextField
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="github"
            hint="Lowercased. Used as the server id."
            required
          />
          <TextField
            label="Command"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder="npx"
            required
          />
          <TextField
            label="Arguments"
            value={argsStr}
            onChange={(e) => setArgsStr(e.target.value)}
            placeholder="-y @modelcontextprotocol/server-github"
            hint="Space-separated; wrap values with spaces in quotes."
          />

          {argsStr.trim() && (
            <div className="rounded-lg border border-subtle/10 bg-surface-3/50 px-3 py-2">
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-content-muted">
                Parsed as
              </div>
              <div className="flex flex-wrap gap-1">
                {tokenizeArgs(argsStr.trim()).map((tok, i) => (
                  <span
                    key={i}
                    className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-content-secondary"
                  >
                    {tok}
                  </span>
                ))}
              </div>
            </div>
          )}

          {addMsg && (
            <div
              className={cn(
                'rounded-xl border px-3 py-2 text-xs',
                addMsg.ok
                  ? 'border-success/25 bg-success/[0.08] text-success'
                  : 'border-danger/25 bg-danger/[0.08] text-danger'
              )}
            >
              {addMsg.text}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-1">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => {
                setAddOpen(false);
                setAddMsg(null);
              }}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              variant="primary"
              loading={adding}
              disabled={!name.trim() || !command.trim()}
            >
              Add & connect
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete confirm */}
      <Modal
        open={pendingDelete !== null}
        onClose={() => setPendingDelete(null)}
        title={`Remove ${pendingDelete ?? ''}?`}
        description="The server is unregistered and its tools are removed from JARVIS."
        size="sm"
        footer={
          <>
            <Button size="sm" variant="ghost" onClick={() => setPendingDelete(null)}>
              Cancel
            </Button>
            <Button
              size="sm"
              variant="danger"
              icon={<Trash2 />}
              loading={busy === pendingDelete}
              onClick={() => pendingDelete && void handleDelete(pendingDelete)}
            >
              Remove
            </Button>
          </>
        }
      >
        <p className="text-xs leading-relaxed text-content-secondary">
          This only removes it from JARVIS — nothing is uninstalled from your system.
        </p>
      </Modal>
    </div>
  );
};
