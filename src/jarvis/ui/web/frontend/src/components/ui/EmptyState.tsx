import React from 'react';
import { cn } from '../../utils/cn';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
  compact?: boolean;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className,
  compact,
}) => (
  <div
    className={cn(
      'flex flex-col items-center justify-center text-center',
      compact ? 'py-8 px-4' : 'py-16 px-6',
      className
    )}
  >
    {icon && (
      <div className="mb-4 flex items-center justify-center w-12 h-12 rounded-2xl bg-accent/10 border border-accent/20 text-accent [&>svg]:w-5 [&>svg]:h-5">
        {icon}
      </div>
    )}
    <h3 className="text-sm font-semibold text-content">{title}</h3>
    {description && (
      <p className="mt-1.5 max-w-sm text-xs leading-relaxed text-content-muted">{description}</p>
    )}
    {action && <div className="mt-5">{action}</div>}
  </div>
);
