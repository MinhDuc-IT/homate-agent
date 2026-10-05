import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'
import { ToggleSwitch } from '@/components/homemind/ToggleSwitch'

interface DeviceCardProps {
  icon: ReactNode
  name: string
  status: string
  active?: boolean
  showToggle?: boolean
  toggleChecked?: boolean
  onToggle?: () => void
  className?: string
}

export function DeviceCard({
  icon,
  name,
  status,
  active = false,
  showToggle = false,
  toggleChecked,
  onToggle,
  className,
}: DeviceCardProps) {
  return (
    <div
      className={cn(
        'flex h-full min-h-[7.5rem] flex-col rounded-lg border border-sidebar-border bg-surface-subtle p-3 transition-colors hover:border-homemind/30',
        className,
      )}
    >
      <div className="flex h-[18px] items-center justify-between">
        <span className={cn(active ? 'text-homemind' : 'text-text-secondary')}>{icon}</span>
        {showToggle ? (
          <span
            role="presentation"
            onClick={(e) => {
              e.stopPropagation()
              onToggle?.()
            }}
            onKeyDown={(e) => e.stopPropagation()}
          >
            <ToggleSwitch checked={toggleChecked ?? active} aria-label={name} />
          </span>
        ) : (
          <span className="inline-block h-[18px] w-8 shrink-0" />
        )}
      </div>
      <p className="mt-2 line-clamp-2 min-h-10 text-sm font-medium leading-5 text-text-primary">
        {name}
      </p>
      <p className="mt-auto line-clamp-2 min-h-8 pt-0.5 text-xs leading-4 text-text-secondary">
        {status}
      </p>
    </div>
  )
}
