import { API_DASHBOARD } from '@/config/api'

let accessToken = ''

export function getAccessToken(): string {
  return accessToken
}

export function setAccessToken(token: string): void {
  accessToken = token
}

export function clearAccessToken(): void {
  accessToken = ''
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string | unknown }
    if (typeof data.detail === 'string') return data.detail
    return JSON.stringify(data.detail ?? data)
  } catch {
    return response.statusText || `HTTP ${response.status}`
  }
}

let refreshInFlight: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight
  refreshInFlight = (async () => {
    const response = await fetch(`${API_DASHBOARD}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    })
    if (!response.ok) {
      clearAccessToken()
      return false
    }
    const data = (await response.json()) as { access_token?: string }
    if (!data.access_token) {
      clearAccessToken()
      return false
    }
    setAccessToken(data.access_token)
    return true
  })()
  try {
    return await refreshInFlight
  } finally {
    refreshInFlight = null
  }
}

type ApiFetchOptions = RequestInit & {
  skipAuth?: boolean
  skipRefresh?: boolean
}

export async function apiFetch(url: string, init: ApiFetchOptions = {}): Promise<Response> {
  const { skipAuth, skipRefresh, headers: initHeaders, ...rest } = init
  const headers = new Headers(initHeaders)
  if (!skipAuth && accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }
  const response = await fetch(url, {
    ...rest,
    headers,
    credentials: 'include',
  })
  if (response.status !== 401 || skipAuth || skipRefresh) {
    return response
  }
  const ok = await tryRefresh()
  if (!ok) return response
  const retryHeaders = new Headers(initHeaders)
  retryHeaders.set('Authorization', `Bearer ${accessToken}`)
  return fetch(url, {
    ...rest,
    headers: retryHeaders,
    credentials: 'include',
  })
}

export async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return (await response.json()) as T
}

export { parseError }
