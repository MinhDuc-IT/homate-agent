import type { ReactNode } from 'react'
import { ApiLoadingBar } from '@/components/ui/ApiLoadingBar'

export function LoadingProvider({ children }: { children: ReactNode }) {
  return (
    <>
      <ApiLoadingBar />
      {children}
    </>
  )
}
