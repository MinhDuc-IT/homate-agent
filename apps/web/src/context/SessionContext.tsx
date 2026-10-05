import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { fetchHome, type HomeMember, type HomeRoom } from '@/api/home'
import { loginRequest, logoutRequest, refreshRequest } from '@/api/auth'

export type UserRole = 'member' | 'admin'

export interface Session {
  memberId: string
  memberName: string
  role: UserRole
}

interface SessionContextValue {
  session: Session | null
  isAdmin: boolean
  authReady: boolean
  houseName: string
  members: HomeMember[]
  rooms: HomeRoom[]
  homeLoading: boolean
  homeError: string | null
  reloadHome: () => Promise<void>
  login: (memberId: string, pin: string) => Promise<void>
  logout: () => Promise<void>
}

const SessionContext = createContext<SessionContextValue | null>(null)

function sessionFromUser(user: { id: string; name: string; role: UserRole }): Session {
  return { memberId: user.id, memberName: user.name, role: user.role }
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [authReady, setAuthReady] = useState(false)
  const [houseName, setHouseName] = useState('')
  const [members, setMembers] = useState<HomeMember[]>([])
  const [rooms, setRooms] = useState<HomeRoom[]>([])
  const [homeLoading, setHomeLoading] = useState(true)
  const [homeError, setHomeError] = useState<string | null>(null)

  const reloadHome = useCallback(async () => {
    const home = await fetchHome()
    setHouseName(home.name)
    setMembers(home.members)
    setRooms(home.rooms ?? [])
    setHomeError(null)
  }, [])

  useEffect(() => {
    let cancelled = false
    setHomeLoading(true)
    Promise.all([
      fetchHome(),
      refreshRequest().catch(() => null),
    ])
      .then(([home, tokens]) => {
        if (cancelled) return
        setHouseName(home.name)
        setMembers(home.members)
        setRooms(home.rooms ?? [])
        setHomeError(null)
        if (tokens?.user) {
          setSession(sessionFromUser(tokens.user))
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setHomeError(err instanceof Error ? err.message : 'Không tải được thông tin nhà')
      })
      .finally(() => {
        if (cancelled) return
        setHomeLoading(false)
        setAuthReady(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (memberId: string, pin: string) => {
    const data = await loginRequest(memberId, pin)
    setSession(sessionFromUser(data.user))
  }, [])

  const logout = useCallback(async () => {
    await logoutRequest()
    setSession(null)
  }, [])

  const value = useMemo(
    () => ({
      session,
      isAdmin: session?.role === 'admin',
      authReady,
      houseName,
      members,
      rooms,
      homeLoading,
      homeError,
      reloadHome,
      login,
      logout,
    }),
    [session, authReady, houseName, members, rooms, homeLoading, homeError, reloadHome, login, logout],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession() {
  const context = useContext(SessionContext)
  if (!context) {
    throw new Error('useSession must be used within SessionProvider')
  }
  return context
}
