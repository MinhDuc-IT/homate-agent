import { forwardRef, type InputHTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  hasError?: boolean
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, hasError, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          'h-10 w-full rounded-lg border border-sidebar-border bg-elevated px-3 text-sm text-text-primary shadow-sm',
          'placeholder:text-text-muted',
          'focus:border-homemind focus:outline-none focus:ring-2 focus:ring-homemind/20',
          'disabled:cursor-not-allowed disabled:bg-surface-subtle disabled:opacity-70',
          hasError && 'border-danger focus:ring-danger/20',
          className,
        )}
        {...props}
      />
    )
  },
)

Input.displayName = 'Input'
