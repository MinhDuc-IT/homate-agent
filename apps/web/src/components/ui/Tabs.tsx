import {
  createContext,
  useContext,
  useMemo,
  type ButtonHTMLAttributes,
  type ReactNode,
} from 'react'
import { cn } from '@/utils/cn'

interface TabsContextValue {
  value: string
  onChange: (value: string) => void
}

const TabsContext = createContext<TabsContextValue | null>(null)

function useTabsContext() {
  const context = useContext(TabsContext)
  if (!context) {
    throw new Error('Tabs components must be used within <Tabs>')
  }
  return context
}

export interface TabsProps {
  value: string
  onChange: (value: string) => void
  children: ReactNode
  className?: string
  variant?: 'underline' | 'boxed'
}

export function Tabs({
  value,
  onChange,
  children,
  className,
  variant = 'underline',
}: TabsProps) {
  const contextValue = useMemo(() => ({ value, onChange }), [value, onChange])

  return (
    <TabsContext.Provider value={contextValue}>
      <div className={className} data-variant={variant}>
        {children}
      </div>
    </TabsContext.Provider>
  )
}

export function TabList({
  children,
  className,
  variant = 'underline',
}: {
  children: ReactNode
  className?: string
  variant?: 'underline' | 'boxed'
}) {
  return (
    <div
      className={cn(
        variant === 'underline' &&
          'mb-5 flex border-b border-sidebar-border',
        variant === 'boxed' &&
          'flex overflow-hidden rounded-xl border border-sidebar-border bg-elevated p-1 shadow-card',
        className,
      )}
      role="tablist"
    >
      {children}
    </div>
  )
}

export function Tab({
  value,
  children,
  className,
  variant = 'underline',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  value: string
  variant?: 'underline' | 'boxed'
}) {
  const { value: activeValue, onChange } = useTabsContext()
  const isActive = activeValue === value

  return (
    <button
      type="button"
      role="tab"
      aria-selected={isActive}
      onClick={() => onChange(value)}
      className={cn(
        'flex-1 px-4 py-3 text-sm font-medium transition-colors',
        variant === 'underline' && [
          'border-b-2 -mb-px',
          isActive
            ? 'border-homemind text-homemind'
            : 'border-transparent text-text-muted hover:text-text-primary',
        ],
        variant === 'boxed' && [
          'text-center',
          isActive
            ? 'bg-homemind-subtle text-homemind'
            : 'text-text-muted hover:bg-surface-subtle hover:text-text-primary',
        ],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}

export function TabPanel({
  value,
  children,
  className,
}: {
  value: string
  children: ReactNode
  className?: string
}) {
  const { value: activeValue } = useTabsContext()
  if (activeValue !== value) return null

  return (
    <div role="tabpanel" className={className}>
      {children}
    </div>
  )
}
