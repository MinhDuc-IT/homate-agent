import { API_DASHBOARD } from '@/config/api'
import { apiFetch, parseError, readJson } from '@/api/http'
import { trackLoading } from '@/utils/loadingTracker'

export type SceneStep = {
  id: string
  sort_order: number
  device_id: string
  device_name: string
  device_kind: string
  action: string
  parameters: Record<string, unknown>
}

export type Scene = {
  id: string
  name: string
  voice_keyword: string
  is_enabled: boolean
  steps: SceneStep[]
}

export type SceneWrite = {
  name: string
  voice_keyword: string
  is_enabled?: boolean
  steps: Array<{
    device_id: string
    action: string
    parameters: Record<string, unknown>
  }>
}

export async function fetchScenes(): Promise<Scene[]> {
  return trackLoading(
    (async () => {
      const response = await apiFetch(`${API_DASHBOARD}/scenes`)
      return readJson<Scene[]>(response)
    })(),
  )
}

export async function createScene(body: SceneWrite): Promise<Scene> {
  return trackLoading(
    (async () => {
      const response = await apiFetch(`${API_DASHBOARD}/scenes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      return readJson<Scene>(response)
    })(),
  )
}

export async function updateScene(id: string, body: SceneWrite): Promise<Scene> {
  return trackLoading(
    (async () => {
      const response = await apiFetch(
        `${API_DASHBOARD}/scenes/${encodeURIComponent(id)}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        },
      )
      return readJson<Scene>(response)
    })(),
  )
}

export async function deleteScene(id: string): Promise<void> {
  return trackLoading(
    (async () => {
      const response = await apiFetch(
        `${API_DASHBOARD}/scenes/${encodeURIComponent(id)}`,
        { method: 'DELETE' },
      )
      if (!response.ok) {
        throw new Error(await parseError(response))
      }
    })(),
  )
}
