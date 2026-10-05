import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface FormGridProps {
  children: ReactNode
  columns?: 1 | 2 | 3 | 4
  className?: string
}

const columnStyles = {
  1: 'grid-cols-1',
  2: 'grid-cols-1 md:grid-cols-2',
  3: 'grid-cols-1 md:grid-cols-3',
  4: 'grid-cols-1 md:grid-cols-2 xl:grid-cols-4',
}

export function FormGrid({ children, columns = 2, className }: FormGridProps) {
  return (
    <div className={cn('grid gap-3.5', columnStyles[columns], className)}>
      {children}
    </div>
  )
}
