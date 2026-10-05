import { cn } from '@/utils/cn'

interface ToggleSwitchProps {
  checked?: boolean
  className?: string
  'aria-label'?: string
}

/** Static visual toggle with green active state matching HomeMate theme. */
export function ToggleSwitch({
  checked = false,
  className,
  'aria-label': ariaLabel,
}: ToggleSwitchProps) {
  return (
    <span
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      className={cn(
        'relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out',
        checked ? 'bg-[#2D6A4F]' : 'bg-[#D1D5DB]',
        className,
      )}
    >
      <span
        className={cn(
          'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition-transform duration-200 ease-in-out',
          checked ? 'translate-x-4' : 'translate-x-0',
        )}
      />
    </span>
  )
}

