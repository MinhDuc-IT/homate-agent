import type { ReactNode } from 'react'

interface PageContentProps {
  children: ReactNode
}

export function PageContent({ children }: PageContentProps) {
  return (
    <main className="min-w-0 flex-1 overflow-y-auto bg-transparent">
      <div className="mx-auto min-h-full w-full max-w-4xl px-4 py-5 sm:px-5 lg:px-6 lg:py-6">
        {children}
      </div>
    </main>
  )
}
