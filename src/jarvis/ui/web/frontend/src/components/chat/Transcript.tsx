import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { ArrowDown } from 'lucide-react';
import { useJarvis } from '../../context/JarvisContext';
import { cn } from '../../utils/cn';
import { MessageItem } from './MessageItem';

/** How close to the bottom still counts as "pinned to latest", in px. */
const STICK_THRESHOLD = 96;

export const Transcript: React.FC = () => {
  const { messages, regenerate, editAndResend } = useJarvis();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [pinned, setPinned] = useState(true);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
  }, []);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    setPinned(distance < STICK_THRESHOLD);
  }, []);

  // Follow streaming output, but never yank the view back if the user has
  // scrolled up to read something.
  useLayoutEffect(() => {
    if (pinned) scrollToBottom('auto');
  }, [messages, pinned, scrollToBottom]);

  // First paint of a loaded session should start at the newest turn.
  useEffect(() => {
    scrollToBottom('auto');
  }, [scrollToBottom]);

  const lastAssistantIndex = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'assistant') return i;
    }
    return -1;
  })();

  return (
    <div className="relative min-h-0 flex-1">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="scroll-area h-full overflow-y-auto px-4 pb-6 pt-6 sm:px-6"
      >
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
          {messages.map((message, i) => (
            <MessageItem
              key={message.id}
              message={message}
              isLast={i === lastAssistantIndex}
              onRegenerate={() => void regenerate()}
              onEdit={(id, text) => void editAndResend(id, text)}
            />
          ))}
        </div>
      </div>

      <button
        onClick={() => scrollToBottom()}
        aria-hidden={pinned}
        tabIndex={pinned ? -1 : 0}
        className={cn(
          'panel absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-1.5 rounded-full px-3 py-1.5',
          'text-xs font-medium text-content-secondary shadow-panel transition-all duration-200',
          pinned
            ? 'pointer-events-none translate-y-2 opacity-0'
            : 'opacity-100 hover:border-accent/35 hover:text-content'
        )}
      >
        <ArrowDown className="h-3.5 w-3.5" />
        Jump to latest
      </button>
    </div>
  );
};
