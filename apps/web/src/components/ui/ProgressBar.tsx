import { cn } from '@/utils/cn'

const fillColors = {
  homemind: 'bg-homemind',
  success: 'bg-success',
  warning: 'bg-warning',
  info: 'bg-info',
  error: 'bg-danger',
} as const

export type ProgressColor = keyof typeof fillColors

export interface ProgressBarProps {
  value: number
  max?: number
  color?: ProgressColor
  className?: string
  barClassName?: string
  showLabel?: boolean
  label?: string
}

export function ProgressBar({
  value,
  max = 100,
  color = 'info',
  className,
  barClassName,
  showLabel = false,
  label,
}: ProgressBarProps) {
  const percent = Math.min(Math.max((value / max) * 100, 0), 100)

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div
        className={cn(
          'h-1.5 flex-1 overflow-hidden rounded-sm bg-border-light',
          barClassName,
        )}
      >
        <div
          className={cn('h-full rounded-sm transition-all', fillColors[color])}
          style={{ width: `${percent}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-[10px] font-bold text-text-secondary">
          {label ?? `${percent.toFixed(1)}%`}
        </span>
      )}
    </div>
  )
}
