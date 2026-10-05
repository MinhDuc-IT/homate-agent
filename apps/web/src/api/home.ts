import { API_DASHBOARD } from '@/config/api'
import { apiFetch, readJson } from '@/api/http'
import { trackLoading } from '@/utils/loadingTracker'

export type HomeMember = {
  id: string
  name: string
  initial: string
  role: 'admin' | 'member'
}

export type HomeRoom = {
  id: string
  label: string
}

export type HomeProfile = {
  id: string
  name: string
  timezone: string
  members: HomeMember[]
  rooms: HomeRoom[]
}

export async function fetchHome(): Promise<HomeProfile> {
  return trackLoading(
    (async () => {
      const response = await apiFetch(`${API_DASHBOARD}/home`, { skipAuth: true })
      return readJson<HomeProfile>(response)
    })(),
  )
}
