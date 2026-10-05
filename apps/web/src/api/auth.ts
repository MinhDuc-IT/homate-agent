import { API_DASHBOARD } from '@/config/api'
import { apiFetch, readJson, setAccessToken, clearAccessToken } from '@/api/http'
import type { HomeMember } from '@/api/home'

export type AuthUser = HomeMember

export type TokenResponse = {
  access_token: string
  token_type: string
  expires_in: number
  user: AuthUser
}

export async function loginRequest(userId: string, pin: string): Promise<TokenResponse> {
  const response = await apiFetch(`${API_DASHBOARD}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, pin }),
    skipAuth: true,
    skipRefresh: true,
  })
  const data = await readJson<TokenResponse>(response)
  setAccessToken(data.access_token)
  return data
}

export async function refreshRequest(): Promise<TokenResponse | null> {
  const response = await apiFetch(`${API_DASHBOARD}/auth/refresh`, {
    method: 'POST',
    skipAuth: true,
    skipRefresh: true,
  })
  if (!response.ok) return null
  const data = (await response.json()) as TokenResponse
  if (!data.access_token) return null
  setAccessToken(data.access_token)
  return data
}

export async function logoutRequest(): Promise<void> {
  try {
    await apiFetch(`${API_DASHBOARD}/auth/logout`, {
      method: 'POST',
      skipAuth: true,
      skipRefresh: true,
    })
  } finally {
    clearAccessToken()
  }
}
