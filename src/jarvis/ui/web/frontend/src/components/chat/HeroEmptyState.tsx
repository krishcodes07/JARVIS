import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';
import { JarvisBlob } from '../JarvisBlob';
import { useJarvis } from '../../context/JarvisContext';

export interface HeroEmptyStateProps {
  className?: string;
}

/**
 * The landing surface: a large centred orb with a subtle status line.
 * Clicking the orb starts the inline voice chat.
 */
export const HeroEmptyState: React.FC<HeroEmptyStateProps> = ({ className }) => {
  const { startVoiceChat } = useJarvis();

  return (
    <div className={cn('relative flex min-h-0 flex-1 flex-col items-center justify-center px-4', className)}>
      <motion.div
        className="flex flex-col items-center"
        initial={{ opacity: 0, scale: 0.85 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      >
        {/* The hero blob — large & interactive */}
        <JarvisBlob
          size={352}
          label="Start voice chat"
          onClick={() => void startVoiceChat().catch((e) => console.warn(e))}
        />

        {/* Status text */}
        <motion.p
          className="mt-6 font-mono text-[13px] font-semibold tracking-[0.15em] text-content-muted"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3, ease: 'easeOut' }}
        >
          Jarvis Online. At Your Service, Sir
        </motion.p>
      </motion.div>
    </div>
  );
};
