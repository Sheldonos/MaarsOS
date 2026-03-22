import { clsx } from 'clsx';
import { HTMLAttributes, forwardRef } from 'react';

interface StatusDotProps extends HTMLAttributes<HTMLSpanElement> {
  status: 'online' | 'offline' | 'pending' | 'error' | 'warning';
  size?: 'sm' | 'md' | 'lg';
  pulse?: boolean;
}

const StatusDot = forwardRef<HTMLSpanElement, StatusDotProps>(
  ({ className, status, size = 'md', pulse = false, ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={clsx(
          'inline-block rounded-full',
          {
            // Status colors
            'bg-green': status === 'online',
            'bg-text-dim': status === 'offline',
            'bg-yellow': status === 'pending' || status === 'warning',
            'bg-red': status === 'error',
            
            // Sizes
            'w-1.5 h-1.5': size === 'sm',
            'w-2 h-2': size === 'md',
            'w-3 h-3': size === 'lg',
            
            // Pulse animation
            'animate-pulse': pulse,
          },
          className
        )}
        {...props}
      />
    );
  }
);

StatusDot.displayName = 'StatusDot';

export default StatusDot;

// Made with Bob
