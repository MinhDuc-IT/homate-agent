import { forwardRef, type SelectHTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  hasError?: boolean
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, hasError, children, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={cn(
          'h-10 min-w-[120px] rounded-lg border border-sidebar-border bg-elevated px-3 text-sm text-text-primary shadow-sm',
          'focus:border-homemind focus:outline-none focus:ring-2 focus:ring-homemind/20',
          'disabled:cursor-not-allowed disabled:bg-surface-subtle disabled:opacity-70',
          hasError && 'border-danger',
          className,
        )}
        {...props}
      >
        {children}
      </select>
    )
  },
)

Select.displayName = 'Select'
