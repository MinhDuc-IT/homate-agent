import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface FormFieldProps {
  label: string
  required?: boolean
  children: ReactNode
  className?: string
  hint?: string
  /** Viết tắt công thức hiển thị cạnh nhãn, VD: @KL */
  abbr?: string
}

export function FormField({
  label,
  required,
  children,
  className,
  hint,
  abbr,
}: FormFieldProps) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label className="flex flex-wrap items-center gap-x-1.5 text-sm font-medium text-text-primary">
        <span>
          {label}
          {required && <span className="text-homemind"> *</span>}
        </span>
        {abbr && (
          <code className="rounded bg-homemind-subtle px-1.5 py-0.5 font-mono text-[10px] font-semibold text-homemind">
            {abbr}
          </code>
        )}
      </label>
      {children}
      {hint && <p className="text-xs text-text-muted">{hint}</p>}
    </div>
  )
}
