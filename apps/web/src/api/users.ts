import { API_DASHBOARD } from '@/config/api'
import { apiFetch, parseError, readJson } from '@/api/http'

export type UserProfile = {
  id: string
  name: string
  initial: string
  role: 'admin' | 'member'
  email: string | null
  phone: string | null
  is_active: boolean
}

export type UserWrite = {
  name: string
  role: 'admin' | 'member'
  email?: string | null
  phone?: string | null
  pin?: string
}

export async function fetchMyProfile(): Promise<UserProfile> {
  return readJson<UserProfile>(await apiFetch(`${API_DASHBOARD}/users/me`))
}

export async function fetchUsers(): Promise<UserProfile[]> {
  return readJson<UserProfile[]>(await apiFetch(`${API_DASHBOARD}/users`))
}

export async function createUser(data: UserWrite & { pin: string }): Promise<UserProfile> {
  return readJson<UserProfile>(await apiFetch(`${API_DASHBOARD}/users`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }))
}

export async function updateUser(id: string, data: Partial<UserWrite>): Promise<UserProfile> {
  return readJson<UserProfile>(await apiFetch(`${API_DASHBOARD}/users/${encodeURIComponent(id)}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }))
}

export async function deleteUser(id: string): Promise<void> {
  const response = await apiFetch(`${API_DASHBOARD}/users/${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (!response.ok) throw new Error(await parseError(response))
}
