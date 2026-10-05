import { ChevronLeftIcon } from '@/assets/icons/CommonIcons'
import { cn } from '@/utils/cn'

export interface BackButtonProps {
  label?: string
  onClick: () => void
  className?: string
}

export function BackButton({
  label = 'Quay lại',
  onClick,
  className,
}: BackButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'mb-3 inline-flex items-center gap-1 rounded border border-homemind/40 bg-elevated px-3 py-1.5 text-xs font-semibold text-homemind',
        'hover:bg-homemind-subtle',
        className,
      )}
    >
      <ChevronLeftIcon />
      {label}
    </button>
  )
}
