import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface PillProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode
  active?: boolean
  accentColor?: string
}

export function Pill({
  children,
  active = false,
  accentColor,
  className,
  type = 'button',
  ...props
}: PillProps) {
  return (
    <button
      type={type}
      className={cn(
        'rounded px-3 py-1 text-[11px] font-semibold border-[1.5px] transition-colors',
        active
          ? 'border-homemind bg-homemind text-homemind-fg'
          : 'border-border-light bg-elevated text-text-primary hover:border-homemind hover:text-homemind',
        className,
      )}
      style={
        !active && accentColor
          ? { borderLeftWidth: 3, borderLeftColor: accentColor }
          : undefined
      }
      {...props}
    >
      {children}
    </button>
  )
}
