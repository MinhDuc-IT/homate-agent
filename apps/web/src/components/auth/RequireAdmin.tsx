import { Navigate } from 'react-router-dom'
import { useSession } from '@/context/SessionContext'
import { ROUTES } from '@/config/routes'

export function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { session, isAdmin } = useSession()

  if (!session) {
    return <Navigate to={ROUTES.login} replace />
  }

  if (!isAdmin) {
    return <Navigate to={ROUTES.dashboard} replace />
  }

  return children
}
