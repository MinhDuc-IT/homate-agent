import type { ReactNode } from 'react'
import { DevicesProvider } from '@/context/DevicesContext'
import { LoadingProvider } from '@/context/LoadingContext'
import { SessionProvider } from '@/context/SessionContext'
import { ToastProvider } from '@/context/ToastContext'

export function Providers({ children }: { children: ReactNode }) {
  return (
    <LoadingProvider>
      <ToastProvider>
        <SessionProvider>
          <DevicesProvider>{children}</DevicesProvider>
        </SessionProvider>
      </ToastProvider>
    </LoadingProvider>
  )
}
