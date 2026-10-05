import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface PageActionsProps {
  children?: ReactNode
  className?: string
}

export function PageActions({ children, className }: PageActionsProps) {
  if (!children) return null

  return (
    <div className={cn('mb-4 flex flex-wrap items-center justify-end gap-2', className)}>
      {children}
    </div>
  )
}
