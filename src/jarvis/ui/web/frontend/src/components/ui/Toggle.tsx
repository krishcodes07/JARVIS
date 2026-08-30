import React, { useId } from 'react';
import { cn } from '../../utils/cn';

export interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
  size?: 'sm' | 'md';
  className?: string;
}

export const Toggle: React.FC<ToggleProps> = ({
  checked,
  onChange,
  disabled,
  label,
  size = 'md',
  className,
}) => {
  const id = useId();
  const track = size === 'sm' ? 'w-9 h-5' : 'w-11 h-6';
  const knob = size === 'sm' ? 'w-3.5 h-3.5' : 'w-[18px] h-[18px]';
  const travel = size === 'sm' ? 'translate-x-4' : 'translate-x-5';

  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative shrink-0 rounded-full transition-colors duration-200',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 focus-visible:ring-offset-2 focus-visible:ring-offset-void',
        'disabled:opacity-40 disabled:pointer-events-none',
        track,
        checked ? 'bg-accent shadow-accent-sm' : 'bg-surface-2 border border-subtle/15',
        className
      )}
    >
      <span
        className={cn(
          'absolute top-1/2 left-[3px] -translate-y-1/2 rounded-full transition-transform duration-200 ease-spring',
          knob,
          checked ? `${travel} bg-white` : 'translate-x-0 bg-content-muted'
        )}
      />
    </button>
  );
};
