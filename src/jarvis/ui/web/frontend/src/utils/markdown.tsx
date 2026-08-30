import React, { memo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Check, Copy, ExternalLink } from 'lucide-react';
import { cn } from './cn';

export interface MarkdownProps {
  content: string;
  className?: string;
}

const CodeBlock: React.FC<{ code: string; language: string }> = ({ code, language }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard is unavailable over plain HTTP on some hosts.
    }
  };

  return (
    <div className="my-3 overflow-hidden rounded-xl border border-subtle/12 bg-surface-3/80">
      <div className="flex items-center justify-between border-b border-subtle/10 bg-surface-2/50 px-3.5 py-2">
        <span className="font-mono text-[11px] uppercase tracking-wider text-accent">
          {language}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-medium text-content-muted transition-colors hover:bg-surface-2 hover:text-content"
        >
          {copied ? (
            <Check className="w-3.5 h-3.5 text-success" />
          ) : (
            <Copy className="w-3.5 h-3.5" />
          )}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="scroll-area overflow-x-auto p-4 font-mono text-[13px] leading-relaxed text-content-secondary">
        <code>{code}</code>
      </pre>
    </div>
  );
};

/**
 * Assistant prose renderer.
 *
 * Backed by `react-markdown` + GFM so tables, ordered lists, task lists, links,
 * and emphasis all work — the previous hand-rolled line splitter supported only
 * headings, bullets, bold, and inline code.
 */
export const MarkdownRenderer: React.FC<MarkdownProps> = memo(({ content, className }) => {
  if (!content) return null;

  return (
    <div
      className={cn(
        'text-[15px] font-[450] leading-[1.7] text-content break-words',
        '[&>*:first-child]:mt-0 [&>*:last-child]:mb-0',
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="mt-5 mb-2 font-display text-xl font-bold tracking-tight text-content">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="mt-5 mb-2 font-display text-lg font-bold tracking-tight text-content">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mt-4 mb-1.5 text-base font-semibold text-content">{children}</h3>
          ),
          h4: ({ children }) => (
            <h4 className="mt-3 mb-1 text-sm font-semibold text-content">{children}</h4>
          ),
          p: ({ children }) => <p className="my-2.5 font-[450] text-content leading-relaxed">{children}</p>,
          strong: ({ children }) => (
            <strong className="font-bold text-white">{children}</strong>
          ),
          em: ({ children }) => <em className="italic font-[450] text-content">{children}</em>,
          ul: ({ children }) => (
            <ul className="my-2.5 ml-1 space-y-1.5 font-[450] text-content [&_ul]:mt-1.5 [&_ul]:ml-4">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="my-2.5 ml-5 list-decimal space-y-1.5 font-[450] text-content marker:text-accent [&_ol]:mt-1.5">
              {children}
            </ol>
          ),
          li: ({ children, className: liClass }) => {
            // GFM task-list items already render their own checkbox.
            const isTask = typeof liClass === 'string' && liClass.includes('task-list-item');
            if (isTask) {
              return (
                <li className="flex items-start gap-2 [&>input]:mt-1 [&>input]:accent-accent">
                  {children}
                </li>
              );
            }
            return (
              <li className="relative pl-5 before:absolute before:left-1 before:top-[0.62em] before:h-1.5 before:w-1.5 before:rounded-full before:bg-accent/70">
                {children}
              </li>
            );
          },
          blockquote: ({ children }) => (
            <blockquote className="my-3 rounded-r-lg border-l-2 border-accent/50 bg-accent/[0.06] py-1.5 pl-3.5 pr-3 font-[450] text-content">
              {children}
            </blockquote>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-baseline gap-0.5 font-semibold text-accent underline decoration-accent/40 underline-offset-2 transition-colors hover:decoration-accent"
            >
              {children}
              <ExternalLink className="w-3 h-3 self-center opacity-70" />
            </a>
          ),
          hr: () => <hr className="my-5 border-subtle/12" />,
          table: ({ children }) => (
            <div className="scroll-area my-3 overflow-x-auto rounded-xl border border-subtle/12">
              <table className="w-full border-collapse text-sm font-[450] text-content">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-surface-2/60">{children}</thead>,
          th: ({ children }) => (
            <th className="border-b border-subtle/12 px-3.5 py-2 text-left text-xs font-semibold uppercase tracking-wider text-content-muted">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-subtle/[0.06] px-3.5 py-2 align-top">{children}</td>
          ),
          code: ({ className: codeClass, children }) => {
            const match = /language-(\w+)/.exec(codeClass || '');
            const text = String(children ?? '').replace(/\n$/, '');

            // Fenced blocks carry a language class or contain newlines; the rest
            // are inline spans.
            if (match || text.includes('\n')) {
              return <CodeBlock code={text} language={match?.[1] || 'text'} />;
            }
            return (
              <code className="rounded border border-accent/20 bg-surface-3/80 px-1.5 py-0.5 font-mono text-[0.85em] text-accent-soft">
                {children}
              </code>
            );
          },
          pre: ({ children }) => <>{children}</>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});
MarkdownRenderer.displayName = 'MarkdownRenderer';
