import React from 'react';
import { cn } from '../../utils/cn';

export interface SkeletonProps {
  className?: string;
}

/** Shimmering placeholder. The shimmer is animation-gated, so it freezes when
 *  the user disables animations. */
export const Skeleton: React.FC<SkeletonProps> = ({ className }) => (
  <div
    aria-hidden
    className={cn(
      'relative overflow-hidden rounded-lg bg-surface-2/70',
      'after:absolute after:inset-0 after:animate-shimmer',
      'after:bg-gradient-to-r after:from-transparent after:via-[rgb(var(--border-subtle)/0.12)] after:to-transparent',
      className
    )}
  />
);

export const SkeletonRows: React.FC<{ count?: number; className?: string }> = ({
  count = 3,
  className,
}) => (
  <div className={cn('space-y-2', className)}>
    {Array.from({ length: count }).map((_, i) => (
      <Skeleton key={i} className="h-14 w-full rounded-xl" />
    ))}
  </div>
);
