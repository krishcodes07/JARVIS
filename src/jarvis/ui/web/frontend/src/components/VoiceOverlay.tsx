import React, { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Loader2, Volume2, X } from 'lucide-react';
import { useJarvis } from '../context/JarvisContext';
import { useTheme } from '../context/ThemeContext';
import { cn } from '../utils/cn';
import { MarkdownRenderer } from '../utils/markdown';
import { JarvisBlob } from './JarvisBlob';

/**
 * Inline voice chat overlay. When active, the blob moves to centre at large
 * size, the input box fades away, and a spacious live transcript appears below
 * the blob showing the latest user/AI exchange. The mic auto-sends after
 * speech ends, JARVIS speaks the response with TTS, and then auto-resumes listening.
 */
export const VoiceOverlay: React.FC = () => {
  const {
    isVoiceChatActive,
    voiceStatus,
    voiceError,
    liveVoiceTranscript,
    voiceChatUserMsg,
    voiceChatAiMsg,
    voiceToolName,
    endVoiceChat,
    stopTts,
    isGenerating,
  } = useJarvis();
  const { enableAnimations } = useTheme();

  // Two-stage Escape:
  // 1st press while speaking → stop TTS, resume listening
  // 2nd press (or 1st when not speaking) → close voice mode
  useEffect(() => {
    if (!isVoiceChatActive) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        if (voiceStatus === 'speaking') {
          stopTts();
        } else {
          endVoiceChat();
        }
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [isVoiceChatActive, voiceStatus, endVoiceChat, stopTts]);

  const transition = enableAnimations
    ? { duration: 0.4, ease: [0.22, 1, 0.36, 1] }
    : { duration: 0 };

  const statusLabel = (() => {
    if (voiceError) return voiceError;
    switch (voiceStatus) {
      case 'listening':
        return 'Listening…';
      case 'transcribing':
        return 'Processing…';
      case 'thinking':
        return voiceToolName
          ? `Using ${voiceToolName}…`
          : 'Thinking…';
      case 'speaking':
        return 'Speaking…';
      default:
        return 'Ready';
    }
  })();

  const statusColor = (() => {
    switch (voiceStatus) {
      case 'listening':
        return 'text-accent';
      case 'transcribing':
        return 'text-content-muted';
      case 'thinking':
        return 'text-accent-soft';
      case 'speaking':
        return 'text-accent-soft';
      default:
        return 'text-content-muted';
    }
  })();

  return (
    <AnimatePresence>
      {isVoiceChatActive && (
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-label="Voice chat"
          className="fixed inset-0 z-[70] flex flex-col items-center justify-center px-4 sm:px-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-void/90 backdrop-blur-2xl" aria-hidden />

          <motion.div
            className="relative flex w-full max-w-3xl flex-col items-center"
            initial={{ scale: 0.85, y: 30 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.85, y: 20 }}
            transition={transition}
          >
            {/* Close button */}
            <button
              onClick={endVoiceChat}
              className={cn(
                'absolute -top-3 right-2 z-10 flex h-9 w-9 items-center justify-center rounded-full',
                'border border-subtle/15 bg-surface-2/70 text-content-muted backdrop-blur-md',
                'transition-all duration-200 hover:border-accent/35 hover:text-content',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60'
              )}
              aria-label="End voice chat"
            >
              <X className="h-4 w-4" />
            </button>

            {/* Centred orb — large, reactive to audio */}
            <JarvisBlob
              size={260}
              isExpanded
              hideFloor
              label="Voice Assistant"
            />

            {/* Status indicator */}
            <motion.div
              className="mt-4 flex items-center gap-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              {(voiceStatus === 'transcribing' || voiceStatus === 'thinking' || isGenerating) && (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-accent/70" />
              )}
              {voiceStatus === 'speaking' && (
                <Volume2 className="h-3.5 w-3.5 animate-pulse text-accent-soft" />
              )}
              {voiceStatus === 'listening' && (
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent/50" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent" />
                </span>
              )}
              <span className={cn('font-mono text-[11px] font-semibold uppercase tracking-[0.25em]', statusColor)}>
                {statusLabel}
              </span>
            </motion.div>

            {/* Unified response area:
                - When user speaks: shows transcribed text with NO background color
                - When Jarvis responds: replaces old speak text with Jarvis response box (compact max-height)
                - No separate user message box */}
            <AnimatePresence mode="wait">
              {voiceChatAiMsg ? (
                <motion.div
                  key="ai-response"
                  className="mt-6 w-full max-w-2xl sm:max-w-3xl"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.25 }}
                >
                  <div className="w-full rounded-2xl border border-subtle/15 bg-surface-2/80 p-4 sm:p-5 text-[14px] leading-relaxed text-content shadow-lg backdrop-blur-xl max-h-36 sm:max-h-40 overflow-y-auto scroll-area">
                    <MarkdownRenderer content={voiceChatAiMsg} />
                  </div>
                </motion.div>
              ) : (liveVoiceTranscript || voiceChatUserMsg) ? (
                <motion.div
                  key="user-speech"
                  className="mt-6 w-full max-w-2xl sm:max-w-3xl flex flex-col items-center justify-center text-center px-4"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.18 }}
                >
                  <p className="text-base sm:text-lg font-medium leading-relaxed text-content/90 tracking-wide">
                    {liveVoiceTranscript || voiceChatUserMsg}
                  </p>
                  {(isGenerating || voiceStatus === 'thinking' || voiceStatus === 'transcribing') && (
                    <div className="mt-3 flex items-center gap-1.5 text-xs text-content-muted">
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent/60 [animation-delay:0ms]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent/60 [animation-delay:150ms]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent/60 [animation-delay:300ms]" />
                    </div>
                  )}
                </motion.div>
              ) : isGenerating ? (
                <motion.div
                  key="generating-dots"
                  className="mt-6 flex justify-center items-center py-3"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <div className="flex items-center gap-1.5 px-3 py-1 text-xs text-content-muted">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent/60 [animation-delay:0ms]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent/60 [animation-delay:150ms]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent/60 [animation-delay:300ms]" />
                  </div>
                </motion.div>
              ) : null}
            </AnimatePresence>

            {/* Error display */}
            {voiceError && (
              <motion.p
                className="mt-4 text-center text-xs text-danger"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                {voiceError}
              </motion.p>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
