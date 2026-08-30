import React from 'react';
import { cn } from '../../utils/cn';

export type BadgeTone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

const TONES: Record<BadgeTone, string> = {
  neutral: 'bg-surface-2 text-content-secondary border-subtle/15',
  accent: 'bg-accent/12 text-accent border-accent/25',
  success: 'bg-success/12 text-success border-success/25',
  warning: 'bg-warning/12 text-warning border-warning/25',
  danger: 'bg-danger/12 text-danger border-danger/25',
  info: 'bg-info/12 text-info border-info/25',
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  /** Leading status dot. */
  dot?: boolean;
  pulse?: boolean;
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  tone = 'neutral',
  dot,
  pulse,
  icon,
  className,
  children,
  ...rest
}) => (
  <span
    className={cn(
      'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border',
      'text-[10px] font-semibold uppercase tracking-wider whitespace-nowrap',
      TONES[tone],
      className
    )}
    {...rest}
  >
    {dot && (
      <span className="relative flex w-1.5 h-1.5">
        {pulse && (
          <span className="absolute inset-0 rounded-full bg-current opacity-60 animate-ping" />
        )}
        <span className="relative w-1.5 h-1.5 rounded-full bg-current" />
      </span>
    )}
    {icon && <span className="[&>svg]:w-3 [&>svg]:h-3">{icon}</span>}
    {children}
  </span>
);
