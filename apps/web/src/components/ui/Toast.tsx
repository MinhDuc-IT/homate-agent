import { cn } from '@/utils/cn'

export type ToastType = 'success' | 'info' | 'error' | 'warning'

export interface ToastItem {
  id: number
  message: string
  type: ToastType
}

const typeStyles: Record<ToastType, string> = {
  success: 'border-success/25 bg-success-light text-text-primary',
  info: 'border-primary/20 bg-primary-subtle text-text-primary',
  error: 'border-danger/25 bg-danger-light text-text-primary',
  warning: 'border-warning/25 bg-warning-light text-text-primary',
}

const dotStyles: Record<ToastType, string> = {
  success: 'bg-success',
  info: 'bg-primary-light',
  error: 'bg-danger',
  warning: 'bg-warning',
}

export function ToastContainer({ toasts }: { toasts: ToastItem[] }) {
  if (toasts.length === 0) return null

  return (
    <div className="fixed right-4 bottom-4 z-[1100] flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            'flex min-w-[260px] max-w-sm items-start gap-2.5 rounded-xl border px-4 py-3 text-sm font-medium shadow-elevated',
            typeStyles[toast.type],
          )}
          role="status"
        >
          <span className={cn('mt-1.5 h-2 w-2 shrink-0 rounded-full', dotStyles[toast.type])} />
          {toast.message}
        </div>
      ))}
    </div>
  )
}
