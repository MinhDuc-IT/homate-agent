import type { ReactNode } from 'react'
import { HomeIcon } from '@/assets/icons/CommonIcons'
import { SITE_NAME } from '@/config/site'

/** Centered shell for auth / guest screens (login, PIN, …). */
export function GuestShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex min-h-full items-center justify-center overflow-hidden bg-surface px-4 py-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(31,213,249,0.1),transparent_55%)]" />
      <div className="relative z-10 w-full max-w-md">
        <div className="mb-6 text-center">
          <span className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-homemind-subtle text-homemind">
            <HomeIcon className="h-6 w-6" />
          </span>
          <p className="font-display text-lg font-bold text-text-primary">{SITE_NAME}</p>
        </div>
        {children}
      </div>
    </div>
  )
}
