import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { CloseIcon } from '@/assets/icons/CommonIcons'
import { cn } from '@/utils/cn'

export interface ModalProps {
  open: boolean
  onClose: () => void
  children: ReactNode
  className?: string
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl'
}

const maxWidthStyles = {
  sm: 'max-w-md',
  md: 'max-w-2xl',
  lg: 'max-w-4xl',
  xl: 'max-w-5xl',
  '2xl': 'max-w-6xl',
}

export function Modal({
  open,
  onClose,
  children,
  className,
  maxWidth = 'lg',
}: ModalProps) {
  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div
      className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      onClick={onClose}
      role="presentation"
    >
      <div
        className={cn(
          'flex max-h-[94vh] w-full flex-col overflow-hidden rounded-2xl border border-sidebar-border bg-elevated shadow-elevated',
          maxWidthStyles[maxWidth],
          className,
        )}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {children}
      </div>
    </div>,
    document.body,
  )
}

export function ModalHeader({
  title,
  onClose,
  children,
}: {
  title?: ReactNode
  onClose?: () => void
  children?: ReactNode
}) {
  return (
    <div className="sticky top-0 z-10 flex items-center justify-between border-b border-sidebar-border bg-elevated px-6 py-4">
      {children ?? <h2 className="text-lg font-semibold text-text-primary">{title}</h2>}
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-subtle text-text-muted transition-colors hover:bg-homemind-subtle hover:text-homemind"
          aria-label="Close"
        >
          <CloseIcon />
        </button>
      )}
    </div>
  )
}

export function ModalBody({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('overflow-y-auto px-6 py-5', className)}>{children}</div>
  )
}

export function ModalFooter({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'sticky bottom-0 flex justify-end gap-2 border-t border-sidebar-border bg-surface-subtle/80 px-6 py-4',
        className,
      )}
    >
      {children}
    </div>
  )
}
