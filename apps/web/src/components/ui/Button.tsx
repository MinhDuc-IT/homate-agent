import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { cn } from '@/utils/cn'

const variants = {
  primary:
    'bg-homemind text-homemind-fg shadow-sm hover:bg-homemind-dark border-transparent active:scale-[0.98]',
  outline:
    'bg-elevated text-text-primary border-sidebar-border hover:border-homemind/40 hover:bg-homemind-subtle hover:text-homemind shadow-sm',
  success: 'bg-success text-homemind-fg hover:bg-emerald-400 border-transparent shadow-sm',
  info: 'bg-homemind text-homemind-fg hover:bg-homemind-dark border-transparent shadow-sm',
  danger:
    'bg-elevated text-danger border border-danger/30 hover:bg-danger-light shadow-sm',
  ghost:
    'bg-transparent text-text-secondary border-transparent hover:bg-sidebar-hover hover:text-text-primary',
  icon:
    'bg-transparent text-text-muted border border-transparent hover:border-sidebar-border hover:bg-elevated hover:text-homemind shadow-none font-medium',
  iconDanger:
    'bg-transparent text-text-muted border border-transparent hover:border-danger/40 hover:bg-danger-light hover:text-danger shadow-none font-medium',
  compact:
    'bg-transparent text-text-muted border border-transparent hover:border-sidebar-border hover:bg-elevated hover:text-text-primary shadow-none font-medium',
  compactDanger:
    'bg-transparent text-text-muted border border-transparent hover:border-danger/40 hover:bg-danger-light hover:text-danger shadow-none font-medium',
} as const

const sizes = {
  default: 'h-9 px-4 text-sm gap-2',
  sm: 'h-8 px-3 text-xs gap-2',
  lg: 'h-10 px-5 text-sm gap-2',
  xs: 'h-7 min-h-7 px-2 text-[10px] gap-1.5 rounded-md shadow-none',
  icon: 'h-6 w-6 min-h-6 min-w-6 p-0 gap-0 rounded-md shadow-none',
  compact: 'h-6 min-h-6 px-1.5 text-[9px] gap-1 rounded-md shadow-none',
} as const

export type ButtonVariant = keyof typeof variants
export type ButtonSize = keyof typeof sizes

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  leftIcon?: ReactNode
  rightIcon?: ReactNode
}

export function Button({
  variant = 'primary',
  size = 'default',
  loading = false,
  leftIcon,
  rightIcon,
  className,
  children,
  type = 'button',
  disabled,
  ...props
}: ButtonProps) {
  const spinnerOnPrimary = variant === 'primary' || variant === 'success' || variant === 'info'

  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center rounded-lg font-semibold whitespace-nowrap border transition-all duration-150',
        'disabled:pointer-events-none disabled:opacity-60',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {loading ? (
        <LoadingSpinner
          size="sm"
          className={cn(
            spinnerOnPrimary ? 'border-homemind-fg/30 border-t-homemind-fg' : undefined,
          )}
        />
      ) : (
        leftIcon
      )}
      {children}
      {!loading && rightIcon}
    </button>
  )
}
