import React from 'react';
import { cn } from '../../utils/cn';
import { Tooltip } from './Tooltip';

export type IconButtonSize = 'xs' | 'sm' | 'md';

const SIZES: Record<IconButtonSize, string> = {
  xs: 'w-7 h-7 rounded-lg [&>svg]:w-3.5 [&>svg]:h-3.5',
  sm: 'w-8 h-8 rounded-lg [&>svg]:w-4 [&>svg]:h-4',
  md: 'w-10 h-10 rounded-xl [&>svg]:w-[18px] [&>svg]:h-[18px]',
};

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Accessible name; also used as the tooltip label unless `tooltip` is false. */
  label: string;
  size?: IconButtonSize;
  active?: boolean;
  tooltip?: boolean | 'top' | 'bottom' | 'left' | 'right';
  tone?: 'default' | 'danger' | 'accent';
}

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  (
    { label, size = 'sm', active, tooltip = 'top', tone = 'default', className, children, ...rest },
    ref
  ) => {
    const button = (
      <button
        ref={ref}
        aria-label={label}
        aria-pressed={active || undefined}
        className={cn(
          'inline-flex items-center justify-center shrink-0 transition-all duration-200',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60',
          'disabled:opacity-40 disabled:pointer-events-none',
          SIZES[size],
          tone === 'danger'
            ? 'text-content-muted hover:text-danger hover:bg-danger/12'
            : tone === 'accent'
              ? 'text-accent hover:bg-accent/12'
              : 'text-content-muted hover:text-content hover:bg-surface-2/70',
          active && 'bg-accent/15 text-accent hover:bg-accent/20 hover:text-accent',
          className
        )}
        {...rest}
      >
        {children}
      </button>
    );

    if (!tooltip) return button;
    return (
      <Tooltip label={label} side={tooltip === true ? 'top' : tooltip}>
        {button}
      </Tooltip>
    );
  }
);
IconButton.displayName = 'IconButton';
