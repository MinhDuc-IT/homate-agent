import { API_DASHBOARD } from '@/config/api'
import { apiFetch, readJson } from '@/api/http'
import { trackLoading } from '@/utils/loadingTracker'

export type HomeSettings = {
  command_log_enabled: boolean
  command_log_retention_days: number
  hitl_timeout_seconds: number
}

export type CommandLog = {
  id: string
  utterance: string
  intent: string | null
  result: string
  note: string
  session_id: string
  created_at: string
}

export type HitlPolicy = {
  id: string
  device_id: string
  device_name: string
  device_kind: string
  action: string
  require_confirm: boolean
}

export type HitlPolicyWrite = {
  device_id: string
  action: string
  require_confirm: boolean
}

export async function fetchHomeSettings(): Promise<HomeSettings> {
  return trackLoading(
    (async () => {
      const response = await apiFetch(`${API_DASHBOARD}/settings`)
      return readJson<HomeSettings>(response)
    })(),
  )
}

export async function patchHomeSettings(
  body: Partial<HomeSettings>,
): Promise<HomeSettings> {
  return trackLoading(
    (async () => {
      const response = await apiFetch(`${API_DASHBOARD}/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      return readJson<HomeSettings>(response)
    })(),
  )
}

export async function fetchCommandLogs(limit = 50): Promise<CommandLog[]> {
  return trackLoading(
    (async () => {
      const response = await apiFetch(
        `${API_DASHBOARD}/command-logs?limit=${encodeURIComponent(String(limit))}`,
      )
      return readJson<CommandLog[]>(response)
    })(),
  )
}

export async function fetchHitlPolicies(): Promise<HitlPolicy[]> {
  return trackLoading(
    (async () => {
      const response = await apiFetch(`${API_DASHBOARD}/hitl-policies`)
      return readJson<HitlPolicy[]>(response)
    })(),
  )
}

export async function replaceHitlPolicies(
  policies: HitlPolicyWrite[],
): Promise<HitlPolicy[]> {
  return trackLoading(
    (async () => {
      const response = await apiFetch(`${API_DASHBOARD}/hitl-policies`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ policies }),
      })
      return readJson<HitlPolicy[]>(response)
    })(),
  )
}
