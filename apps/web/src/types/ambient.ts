/** Ambient context — weather snapshot + room occupancy mock. */

export type WeatherSnapshot = {
  temp_c: number
  feels_like_c: number
  humidity: number
  condition: string
  description: string
  wind_ms: number
  fetched_at: string
  stale: boolean
}

export type RoomAmbient = {
  id: string
  label: string
  occupied: boolean
  vacant_minutes: number
  indoor_temp_c: number | null
  indoor_humidity: number | null
  devices_on: string[]
}

export type AmbientSnapshot = {
  ts: string
  local_time: string
  part_of_day: string
  weather: WeatherSnapshot | null
  rooms: RoomAmbient[]
}

export type RoomMockPatch = {
  occupied?: boolean
  indoor_temp_c?: number
  indoor_humidity?: number
  vacant_minutes?: number
}

/** WS push from the occupancy watchdog — see backend `ambient.suggestion`. */
export type AmbientSuggestion = {
  type: 'ambient.suggestion'
  session_id: string
  request_id: string
  expires_in_seconds: number
  room: string
  room_label: string
  reason: string
  vacant_minutes: number
  message: string
  audio_format?: string
  audio_base64?: string
  actions: { device_id: string; action: string }[]
}

export type AmbientSuggestionResponse = {
  ok: boolean
  status: 'executed' | 'rejected'
  executed: boolean
  device_ids: string[]
}
