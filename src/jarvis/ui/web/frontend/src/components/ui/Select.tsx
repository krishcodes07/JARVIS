import React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps
  extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'children' | 'size'> {
  options: SelectOption[];
  placeholder?: string;
  /** Control height. Shadows the native numeric `size`, which we never use. */
  size?: 'sm' | 'md';
}

/**
 * Native `<select>` wrapper — keeps mobile pickers and keyboard behaviour for
 * free while matching the token palette.
 */
export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ options, placeholder, size = 'md', className, ...rest }, ref) => (
    <div className="relative inline-flex w-full">
      <select
        ref={ref}
        className={cn(
          'w-full appearance-none bg-surface-2 border border-subtle/15 rounded-xl',
          'text-content font-medium transition-colors duration-200',
          'hover:border-accent/30 focus:border-accent/60 focus:outline-none focus:ring-2 focus:ring-accent/25',
          'disabled:opacity-45 disabled:pointer-events-none',
          size === 'sm' ? 'h-9 pl-3 pr-9 text-xs' : 'h-11 pl-4 pr-10 text-sm',
          className
        )}
        {...rest}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} disabled={opt.disabled}>
            {opt.label}
          </option>
        ))}
      </select>
      <ChevronDown
        className={cn(
          'pointer-events-none absolute top-1/2 -translate-y-1/2 text-content-muted',
          size === 'sm' ? 'right-2.5 w-3.5 h-3.5' : 'right-3.5 w-4 h-4'
        )}
      />
    </div>
  )
);
Select.displayName = 'Select';
