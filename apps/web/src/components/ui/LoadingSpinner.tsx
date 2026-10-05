import { cn } from '@/utils/cn'

const sizeStyles = {
  sm: 'h-4 w-4 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-9 w-9 border-[3px]',
} as const

export type LoadingSpinnerSize = keyof typeof sizeStyles

export interface LoadingSpinnerProps {
  size?: LoadingSpinnerSize
  className?: string
  label?: string
}

export function LoadingSpinner({ size = 'md', className, label = 'Đang tải' }: LoadingSpinnerProps) {
  return (
    <span
      role="status"
      aria-label={label}
      className={cn(
        'inline-block animate-spin rounded-full border-sidebar-border border-t-homemind',
        sizeStyles[size],
        className,
      )}
    />
  )
}
