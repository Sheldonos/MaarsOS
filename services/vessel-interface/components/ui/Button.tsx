import { clsx } from 'clsx';
import { ButtonHTMLAttributes, forwardRef } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={clsx(
          'inline-flex items-center justify-center rounded-md font-medium transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
          'disabled:opacity-50 disabled:pointer-events-none',
          {
            // Variants
            'bg-primary text-bg hover:bg-primary/90': variant === 'primary',
            'bg-surface2 text-text border border-border hover:bg-surface3': variant === 'secondary',
            'bg-red text-white hover:bg-red/90': variant === 'danger',
            'hover:bg-surface2 text-text-dim hover:text-text': variant === 'ghost',
            
            // Sizes
            'h-8 px-3 text-[13px]': size === 'sm',
            'h-10 px-4 text-[13px]': size === 'md',
            'h-12 px-6 text-[14px]': size === 'lg',
          },
          className
        )}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;

// Made with Bob
