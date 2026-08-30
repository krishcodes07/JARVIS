import React, { useEffect, useRef, useState } from 'react';
import { Brain, ChevronRight } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface ThinkingBlockProps {
  thought: string;
  /** True while reasoning tokens are still arriving. */
  isStreaming?: boolean;
}

export const ThinkingBlock: React.FC<ThinkingBlockProps> = ({ thought, isStreaming }) => {
  const [open, setOpen] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);

  // Follow the reasoning as it streams, but only while it's open.
  useEffect(() => {
    if (open && isStreaming && bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [open, isStreaming, thought]);

  if (!thought && !isStreaming) return null;

  return (
    <div className="my-2 overflow-hidden rounded-xl border border-accent/18 bg-accent/[0.05]">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition-colors hover:bg-accent/10"
      >
        <Brain className={cn('h-3.5 w-3.5 shrink-0 text-accent', isStreaming && 'animate-pulse')} />
        <span className="font-medium text-accent-soft">
          {isStreaming ? 'Thinking…' : 'Reasoning'}
        </span>
        {!open && thought && (
          <span className="min-w-0 flex-1 truncate text-content-muted">
            {thought.replace(/\s+/g, ' ').slice(0, 120)}
          </span>
        )}
        <ChevronRight
          className={cn(
            'ml-auto h-3.5 w-3.5 shrink-0 text-content-muted transition-transform',
            open && 'rotate-90'
          )}
        />
      </button>

      {open && (
        <div
          ref={bodyRef}
          className="scroll-area max-h-64 overflow-y-auto border-t border-accent/12 px-3.5 py-3 text-xs leading-relaxed text-content-secondary"
        >
          <div className="whitespace-pre-wrap font-mono">
            {thought || 'Waiting for reasoning tokens…'}
          </div>
        </div>
      )}
    </div>
  );
};
