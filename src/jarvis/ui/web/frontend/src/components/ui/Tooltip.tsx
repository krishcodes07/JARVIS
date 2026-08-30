import React, { useId, useState } from 'react';
import { cn } from '../../utils/cn';

type Side = 'top' | 'bottom' | 'left' | 'right';

const POSITION: Record<Side, string> = {
  top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
  left: 'right-full top-1/2 -translate-y-1/2 mr-2',
  right: 'left-full top-1/2 -translate-y-1/2 ml-2',
};

export interface TooltipProps {
  label: React.ReactNode;
  side?: Side;
  children: React.ReactNode;
  className?: string;
  /** Suppress rendering (e.g. when a label is already visible). */
  disabled?: boolean;
}

/**
 * Lightweight CSS tooltip. Shows on hover and on keyboard focus, and is exposed
 * to assistive tech via `aria-describedby` rather than title text.
 */
export const Tooltip: React.FC<TooltipProps> = ({
  label,
  side = 'top',
  children,
  className,
  disabled,
}) => {
  const [open, setOpen] = useState(false);
  const id = useId();

  if (disabled) return <>{children}</>;

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {React.isValidElement(children)
        ? React.cloneElement(children as React.ReactElement<any>, { 'aria-describedby': id })
        : children}
      <span
        id={id}
        role="tooltip"
        className={cn(
          'pointer-events-none absolute z-[70] whitespace-nowrap rounded-lg px-2.5 py-1.5',
          'bg-surface-3/95 backdrop-blur-md border border-subtle/15 shadow-panel',
          'text-[11px] font-medium text-content-secondary',
          'transition-all duration-150',
          open ? 'opacity-100 scale-100' : 'opacity-0 scale-95',
          POSITION[side],
          className
        )}
      >
        {label}
      </span>
    </span>
  );
};
