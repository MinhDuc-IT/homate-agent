import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

interface TabletScreenProps {
  children: ReactNode
  className?: string
}

/** Root wrapper: fills available main area without page-level scroll. */
export function TabletScreen({ children, className }: TabletScreenProps) {
  return (
    <div
      className={cn(
        'flex h-full min-h-0 flex-col overflow-hidden',
        className,
      )}
    >
      {children}
    </div>
  )
}

interface TabletScrollProps {
  children: ReactNode
  className?: string
}

/** Scrollable region inside a screen (not the whole page). */
export function TabletScroll({ children, className }: TabletScrollProps) {
  return (
    <div
      className={cn(
        'min-h-0 flex-1 overflow-x-hidden overflow-y-auto',
        className,
      )}
    >
      {children}
    </div>
  )
}

interface TabletCardProps {
  children: ReactNode
  className?: string
}

export function TabletCard({ children, className }: TabletCardProps) {
  return (
    <div
      className={cn(
        'rounded-2xl border border-[#E6ECE3] bg-white shadow-sm',
        className,
      )}
    >
      {children}
    </div>
  )
}
