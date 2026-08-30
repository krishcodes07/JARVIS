import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { ArrowUp, Mic, Square } from 'lucide-react';
import { useJarvis } from '../../context/JarvisContext';
import { cn } from '../../utils/cn';
import { IconButton } from '../ui';
import { filterSlashCommands, SlashCommandMenu } from './SlashCommandMenu';

const MAX_HEIGHT = 200;

export interface PromptBoxProps {
  onSlashAction?: (cmd: string) => void;
  /** Override for sendMessage — used by ChatView for routing-aware sends. */
  onSend?: (text: string) => Promise<void>;
  className?: string;
  autoFocus?: boolean;
  placeholder?: string;
}

export const PromptBox: React.FC<PromptBoxProps> = ({
  onSlashAction,
  onSend,
  className,
  autoFocus,
  placeholder = 'Ask JARVIS anything…',
}) => {
  const { sendMessage, stopGeneration, isGenerating, startVoiceChat, isVoiceChatActive } = useJarvis();
  const [text, setText] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const commands = useMemo(() => filterSlashCommands(text), [text]);
  const menuOpen = commands.length > 0 && text.startsWith('/') && !text.includes('\n');

  // Auto-grow. Runs layout-synchronously so the box never flashes at the wrong
  // height; `height: auto` first is required to let scrollHeight shrink again.
  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [text]);

  useEffect(() => {
    setActiveIndex(0);
  }, [commands.length]);

  useEffect(() => {
    if (autoFocus) textareaRef.current?.focus();
  }, [autoFocus]);

  const reset = useCallback(() => {
    setText('');
    const el = textareaRef.current;
    if (el) el.style.height = 'auto';
  }, []);

  const submit = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || isGenerating) return;

    if (trimmed.startsWith('/') && onSlashAction) {
      onSlashAction(trimmed);
      reset();
      return;
    }
    const sender = onSend || sendMessage;
    void sender(trimmed);
    reset();
  }, [isGenerating, onSlashAction, onSend, reset, sendMessage, text]);

  const runCommand = useCallback(
    (name: string) => {
      if (onSlashAction) {
        onSlashAction(name);
        reset();
      } else {
        setText(`${name} `);
      }
      textareaRef.current?.focus();
    },
    [onSlashAction, reset]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (menuOpen) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex((i) => (i + 1) % commands.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((i) => (i - 1 + commands.length) % commands.length);
        return;
      }
      if (e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey)) {
        e.preventDefault();
        runCommand(commands[activeIndex].name);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        reset();
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const canSend = text.trim().length > 0;

  return (
    <div className={cn('relative w-full', className)}>
      {menuOpen && (
        <SlashCommandMenu
          commands={commands}
          activeIndex={activeIndex}
          onSelect={runCommand}
          onHover={setActiveIndex}
        />
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className={cn(
          'panel flex items-end gap-2 rounded-3xl px-3 py-2.5 shadow-panel transition-colors duration-200',
          'focus-within:border-accent/45 focus-within:shadow-accent-md'
        )}
      >
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={1}
          aria-label="Message JARVIS"
          className="scroll-area min-h-[28px] w-full flex-1 resize-none self-center bg-transparent px-2 py-1 text-[15px] leading-6 text-content outline-none placeholder:text-content-muted/70"
        />

        <div className="flex shrink-0 items-center gap-1 pb-0.5">
          <IconButton
            label={isVoiceChatActive ? 'Voice chat active' : 'Voice input'}
            size="sm"
            active={isVoiceChatActive}
            onClick={() => void startVoiceChat().catch((err) => console.warn(err))}
            type="button"
          >
            <Mic />
          </IconButton>

          {isGenerating ? (
            <IconButton
              label="Stop generating"
              size="sm"
              tone="danger"
              type="button"
              onClick={stopGeneration}
              className="bg-danger/12 text-danger"
            >
              <Square />
            </IconButton>
          ) : (
            <button
              type="submit"
              disabled={!canSend}
              aria-label="Send message"
              className={cn(
                'flex h-8 w-8 items-center justify-center rounded-full transition-all duration-200',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60',
                canSend
                  ? 'bg-accent text-white shadow-accent-sm hover:bg-accent-soft active:scale-95'
                  : 'cursor-not-allowed bg-surface-2 text-content-muted/60'
              )}
            >
              <ArrowUp className="h-4 w-4 stroke-[2.5]" />
            </button>
          )}
        </div>
      </form>
    </div>
  );
};
