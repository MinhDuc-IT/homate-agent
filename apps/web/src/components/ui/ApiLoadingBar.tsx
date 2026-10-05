import { useEffect, useState } from 'react'
import { subscribeLoading } from '@/utils/loadingTracker'
import { cn } from '@/utils/cn'

export function ApiLoadingBar() {
  const [pending, setPending] = useState(0)
  const [visible, setVisible] = useState(false)

  useEffect(() => subscribeLoading(setPending), [])

  useEffect(() => {
    if (pending > 0) {
      setVisible(true)
      return
    }

    const timer = window.setTimeout(() => setVisible(false), 280)
    return () => window.clearTimeout(timer)
  }, [pending])

  if (!visible) return null

  return (
    <div
      className="pointer-events-none fixed top-0 right-0 left-0 z-[200] h-0.5 overflow-hidden"
      aria-hidden="true"
    >
      <div
        className={cn(
          'h-full bg-homemind transition-opacity duration-300',
          pending > 0 ? 'animate-api-loading-bar opacity-100' : 'opacity-0',
        )}
      />
    </div>
  )
}
