import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

export function SectionTitle({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <h3
      className={cn(
        'mt-6 mb-3 flex items-center gap-2 font-display text-sm font-semibold text-text-primary',
        className,
      )}
    >
      <span className="h-4 w-1 rounded-full bg-homemind" />
      {children}
    </h3>
  )
}
