import type { ReactNode } from 'react'
import type { StatusVariant } from '@/constants/status'
import { cn } from '@/utils/cn'

const variantStyles: Record<StatusVariant, string> = {
  warning: 'bg-warning-light text-warning ring-1 ring-warning/30',
  pending: 'bg-info-light text-info ring-1 ring-info/30',
  success: 'bg-success-light text-success ring-1 ring-success/30',
  error: 'bg-danger-light text-danger ring-1 ring-danger/30',
  neutral: 'bg-surface-subtle text-text-secondary ring-1 ring-sidebar-border',
}

const dotStyles: Record<StatusVariant, string> = {
  warning: 'bg-warning',
  pending: 'bg-homemind',
  success: 'bg-success',
  error: 'bg-danger',
  neutral: 'bg-text-muted',
}

export interface BadgeProps {
  children: ReactNode
  variant?: StatusVariant
  showDot?: boolean
  className?: string
}

export function Badge({
  children,
  variant = 'neutral',
  showDot = true,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-semibold',
        variantStyles[variant],
        className,
      )}
    >
      {showDot && (
        <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', dotStyles[variant])} />
      )}
      {children}
    </span>
  )
}
