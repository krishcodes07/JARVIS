import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '../../utils/cn';
import { IconButton } from './IconButton';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  description?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
  /** Hide the close affordance for blocking confirmations. */
  hideClose?: boolean;
  className?: string;
}

const SIZES = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
};

export const Modal: React.FC<ModalProps> = ({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
  hideClose,
  className,
}) => {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    // Focus the panel so Escape and Tab land inside the dialog.
    panelRef.current?.focus();
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[80] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
        >
          <div
            className="absolute inset-0 bg-void/80 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden
          />
          <motion.div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            tabIndex={-1}
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 8 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className={cn(
              'relative w-full panel rounded-2xl shadow-panel focus:outline-none',
              'max-h-[85vh] flex flex-col',
              SIZES[size],
              className
            )}
          >
            {(title || !hideClose) && (
              <header className="flex items-start justify-between gap-4 px-5 pt-5 pb-4 border-b border-subtle/10">
                <div className="min-w-0">
                  {title && (
                    <h2 className="text-base font-semibold text-content font-display">{title}</h2>
                  )}
                  {description && (
                    <p className="mt-1 text-xs leading-relaxed text-content-muted">{description}</p>
                  )}
                </div>
                {!hideClose && (
                  <IconButton label="Close" onClick={onClose} tooltip={false}>
                    <X />
                  </IconButton>
                )}
              </header>
            )}
            <div className="flex-1 min-h-0 overflow-y-auto scroll-area px-5 py-4">{children}</div>
            {footer && (
              <footer className="flex items-center justify-end gap-2 px-5 py-4 border-t border-subtle/10">
                {footer}
              </footer>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
};
