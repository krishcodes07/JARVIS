import React, { useState } from 'react';
import { AlertTriangle, Check, ChevronRight, Loader2, Terminal } from 'lucide-react';
import { ToolCall } from '../../types';
import { cn } from '../../utils/cn';
import { AskUserCard } from './AskUserCard';

export interface ToolCallPillProps {
  toolCall: ToolCall;
}

const formatDuration = (ms?: number): string | null => {
  if (ms === undefined || ms < 0) return null;
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(ms < 10_000 ? 1 : 0)}s`;
};

const hasBody = (t: ToolCall) =>
  (t.args && Object.keys(t.args).length > 0) || (t.result && t.result.length > 0);

export const ToolCallPill: React.FC<ToolCallPillProps> = ({ toolCall }) => {
  if (toolCall.tool === 'ask_user' || toolCall.tool === 'ask_question') {
    return <AskUserCard toolCall={toolCall} />;
  }

  const [expanded, setExpanded] = useState(false);
  const { status, tool, args, result, truncated } = toolCall;
  const duration = formatDuration(toolCall.durationMs);
  const expandable = !!hasBody(toolCall);

  return (
    <div
      className={cn(
        'my-1.5 overflow-hidden rounded-xl border bg-surface-2/45 text-xs transition-colors',
        status === 'error' ? 'border-danger/30' : 'border-subtle/10'
      )}
    >
      <button
        onClick={() => expandable && setExpanded((v) => !v)}
        aria-expanded={expanded}
        disabled={!expandable}
        className={cn(
          'flex w-full items-center gap-2 px-3 py-2 text-left transition-colors',
          expandable ? 'hover:bg-surface-2/70' : 'cursor-default'
        )}
      >
        {status === 'running' ? (
          <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-accent" />
        ) : status === 'error' ? (
          <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-danger" />
        ) : (
          <Check className="h-3.5 w-3.5 shrink-0 text-success" />
        )}

        <Terminal className="h-3.5 w-3.5 shrink-0 text-content-muted" />
        <span className="min-w-0 truncate font-mono font-medium text-content">{tool}</span>

        <span
          className={cn(
            'shrink-0 text-[10px] font-semibold uppercase tracking-wider',
            status === 'running'
              ? 'text-accent'
              : status === 'error'
                ? 'text-danger'
                : 'text-success'
          )}
        >
          {status === 'running' ? 'running' : status === 'error' ? 'failed' : 'done'}
        </span>

        <span className="ml-auto flex shrink-0 items-center gap-1.5 text-content-muted">
          {duration && <span className="font-mono text-[10px]">{duration}</span>}
          {expandable && (
            <ChevronRight
              className={cn('h-3.5 w-3.5 transition-transform', expanded && 'rotate-90')}
            />
          )}
        </span>
      </button>

      {expanded && (
        <div className="space-y-2 border-t border-subtle/8 bg-surface-3/60 px-3 py-2.5">
          {args && Object.keys(args).length > 0 && (
            <div>
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-content-muted">
                Arguments
              </div>
              <pre className="scroll-area max-h-40 overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed text-accent-soft">
                {JSON.stringify(args, null, 2)}
              </pre>
            </div>
          )}
          {result && (
            <div>
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-content-muted">
                Result
              </div>
              <pre
                className={cn(
                  'scroll-area max-h-56 overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed',
                  status === 'error' ? 'text-danger' : 'text-content-secondary'
                )}
              >
                {result}
              </pre>
              {truncated && (
                <p className="mt-1.5 text-[10px] italic text-content-muted">
                  Output was truncated for transport.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
