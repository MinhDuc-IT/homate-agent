import { API_DASHBOARD } from '@/config/api'
import { apiFetch, readJson } from '@/api/http'
import type { EnergyPeriod, EnergyReport } from '@/types/energy'
import { trackLoading } from '@/utils/loadingTracker'

export async function fetchEnergy(
  period: EnergyPeriod,
  filters: { roomId?: string; deviceId?: string; anchor?: string } = {},
): Promise<EnergyReport> {
  const params = new URLSearchParams({ period })
  if (filters.roomId) params.set('room_id', filters.roomId)
  if (filters.deviceId) params.set('device_id', filters.deviceId)
  if (filters.anchor) params.set('anchor', filters.anchor)
  return trackLoading(
    (async () => {
      const response = await apiFetch(`${API_DASHBOARD}/energy?${params}`)
      return readJson<EnergyReport>(response)
    })(),
  )
}
