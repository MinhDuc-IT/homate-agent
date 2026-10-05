import { API_DASHBOARD } from '@/config/api'
import { apiFetch, parseError, readJson } from '@/api/http'

export type RecurrenceRule = { frequency: 'daily' | 'weekly'; time: string; days_of_week: number[] }
export type Schedule = {
  id: string; name: string; schedule_type: 'once' | 'recurring'; target_type: 'device_action' | 'scene'
  device_id: string | null; device_name: string | null; room_id: string | null; action: string | null
  parameters: Record<string, unknown>; scene_id: string | null; scene_name: string | null
  timezone: string; run_at: string | null; recurrence_rule: RecurrenceRule | null; next_run_at: string | null
  enabled: boolean; status: 'active' | 'paused' | 'completed' | 'failed'; last_run_at: string | null
}
export type ScheduleWrite = {
  name: string; schedule_type: 'once' | 'recurring'; target_type: 'device_action' | 'scene'
  device_id?: string | null; action?: string | null; parameters?: Record<string, unknown>
  scene_id?: string | null; timezone?: string; run_at?: string | null; recurrence_rule?: RecurrenceRule | null; enabled?: boolean
}

export async function fetchSchedules(filters: { roomId?: string; sceneId?: string } = {}): Promise<Schedule[]> {
  const params = new URLSearchParams()
  if (filters.roomId) params.set('room_id', filters.roomId)
  if (filters.sceneId) params.set('scene_id', filters.sceneId)
  const suffix = params.size ? `?${params}` : ''
  return readJson<Schedule[]>(await apiFetch(`${API_DASHBOARD}/schedules${suffix}`))
}
export async function createSchedule(body: ScheduleWrite): Promise<Schedule> {
  return readJson<Schedule>(await apiFetch(`${API_DASHBOARD}/schedules`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }))
}
export async function updateSchedule(id: string, body: Partial<ScheduleWrite>): Promise<Schedule> {
  return readJson<Schedule>(await apiFetch(`${API_DASHBOARD}/schedules/${encodeURIComponent(id)}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }))
}
export async function deleteSchedule(id: string): Promise<void> {
  const response = await apiFetch(`${API_DASHBOARD}/schedules/${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (!response.ok) throw new Error(await parseError(response))
}
