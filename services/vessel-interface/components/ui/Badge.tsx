import { clsx } from 'clsx';
import { HTMLAttributes, forwardRef } from 'react';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', children, ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={clsx(
          'inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium',
          {
            'bg-surface2 text-text border border-border': variant === 'default',
            'bg-green/10 text-green border border-green/30': variant === 'success',
            'bg-yellow/10 text-yellow border border-yellow/30': variant === 'warning',
            'bg-red/10 text-red border border-red/30': variant === 'danger',
            'bg-primary/10 text-primary border border-primary/30': variant === 'info',
          },
          className
        )}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

export default Badge;

// Made with Bob
