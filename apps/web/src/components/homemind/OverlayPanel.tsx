import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

interface OverlayPanelProps {
  children: ReactNode
  className?: string
}

/** Dimmed backdrop + centered card — wireframe screens 4 & 5. */
export function OverlayPanel({ children, className }: OverlayPanelProps) {
  return (
    <div className="flex min-h-[min(70vh,520px)] items-center justify-center rounded-xl bg-black/55 p-6 backdrop-blur-[2px]">
      <div
        className={cn(
          'w-full max-w-sm rounded-xl border border-sidebar-border bg-elevated p-5 shadow-elevated',
          className,
        )}
      >
        {children}
      </div>
    </div>
  )
}
