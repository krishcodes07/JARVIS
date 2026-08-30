import React, { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface TextFieldProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: string;
  hint?: string;
  error?: string;
  icon?: React.ReactNode;
  /** Renders a reveal toggle and masks the value by default. */
  secret?: boolean;
  /** Control height. Shadows the native numeric `size`, which we never use. */
  size?: 'sm' | 'md';
}

export const TextField = React.forwardRef<HTMLInputElement, TextFieldProps>(
  ({ label, hint, error, icon, secret, size = 'md', className, id, ...rest }, ref) => {
    const [revealed, setRevealed] = useState(false);
    const inputId = id || rest.name || label?.toLowerCase().replace(/\s+/g, '-');

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block mb-1.5 text-xs font-medium text-content-secondary"
          >
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-content-muted [&>svg]:w-4 [&>svg]:h-4">
              {icon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            type={secret && !revealed ? 'password' : rest.type || 'text'}
            aria-invalid={!!error}
            className={cn(
              'w-full bg-surface-2 border rounded-xl text-content placeholder:text-content-muted/70',
              'transition-colors duration-200',
              'focus:outline-none focus:ring-2 focus:ring-accent/25',
              'disabled:opacity-45 disabled:pointer-events-none',
              error
                ? 'border-danger/50 focus:border-danger'
                : 'border-subtle/15 hover:border-accent/25 focus:border-accent/60',
              size === 'sm' ? 'h-9 text-xs' : 'h-11 text-sm',
              icon ? 'pl-10' : 'pl-4',
              secret ? 'pr-11' : 'pr-4',
              className
            )}
            {...rest}
          />
          {secret && (
            <button
              type="button"
              onClick={() => setRevealed((v) => !v)}
              aria-label={revealed ? 'Hide value' : 'Show value'}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-content-muted hover:text-content hover:bg-surface-3/70 transition-colors"
            >
              {revealed ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          )}
        </div>
        {(error || hint) && (
          <p
            className={cn(
              'mt-1.5 text-[11px] leading-relaxed',
              error ? 'text-danger' : 'text-content-muted'
            )}
          >
            {error || hint}
          </p>
        )}
      </div>
    );
  }
);
TextField.displayName = 'TextField';
