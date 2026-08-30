import React from 'react';
import { cn } from '../../utils/cn';

export interface SectionProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  /** Render without the panel chrome (for full-bleed content). */
  bare?: boolean;
}

/**
 * A titled group of settings rows. Every settings panel is composed from these
 * so spacing, dividers, and heading weight stay identical across pages.
 */
export const Section: React.FC<SectionProps> = ({
  title,
  description,
  icon,
  actions,
  children,
  className,
  bare,
}) => (
  <section className={cn('w-full', className)}>
    {(title || actions) && (
      <div className="flex items-start justify-between gap-4 mb-3 px-1">
        <div className="min-w-0">
          {title && (
            <h3 className="flex items-center gap-2 text-sm font-semibold text-content">
              {icon && <span className="text-accent [&>svg]:w-4 [&>svg]:h-4">{icon}</span>}
              {title}
            </h3>
          )}
          {description && (
            <p className="mt-1 text-xs leading-relaxed text-content-muted max-w-prose">
              {description}
            </p>
          )}
        </div>
        {actions && <div className="shrink-0 flex items-center gap-2">{actions}</div>}
      </div>
    )}
    {bare ? (
      <div>{children}</div>
    ) : (
      <div className="panel rounded-2xl overflow-hidden divide-y divide-[rgb(var(--border-subtle)/0.08)]">
        {children}
      </div>
    )}
  </section>
);

export interface RowProps {
  label: React.ReactNode;
  description?: React.ReactNode;
  /** Right-hand control. */
  control?: React.ReactNode;
  icon?: React.ReactNode;
  /** Stack the control beneath the label (for wide inputs). */
  stacked?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export const Row: React.FC<RowProps> = ({
  label,
  description,
  control,
  icon,
  stacked,
  className,
  children,
}) => (
  <div
    className={cn(
      'px-4 py-3.5 transition-colors duration-200 hover:bg-surface-2/25',
      stacked ? 'space-y-3' : 'flex items-center justify-between gap-4',
      className
    )}
  >
    <div className={cn('min-w-0', !stacked && 'flex items-start gap-3')}>
      {icon && !stacked && (
        <span className="mt-0.5 shrink-0 text-content-muted [&>svg]:w-4 [&>svg]:h-4">{icon}</span>
      )}
      <div className="min-w-0">
        <div className="text-sm font-medium text-content">{label}</div>
        {description && (
          <div className="mt-0.5 text-xs leading-relaxed text-content-muted">{description}</div>
        )}
      </div>
    </div>
    {control && <div className={cn(stacked ? 'w-full' : 'shrink-0')}>{control}</div>}
    {children}
  </div>
);
