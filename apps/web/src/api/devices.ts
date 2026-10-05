import { API_DASHBOARD } from '@/config/api'
import { apiFetch, readJson } from '@/api/http'
import type { Device, DeviceStateValue } from '@/types/device'
import { trackLoading } from '@/utils/loadingTracker'

export type DeviceActionResponse = {
  device: Device
  changed_key: string
  previous_value: DeviceStateValue | null
  new_value: DeviceStateValue | null
}

export async function fetchDevices(): Promise<Device[]> {
  return trackLoading(
    (async () => {
      const response = await apiFetch(`${API_DASHBOARD}/devices`)
      return readJson<Device[]>(response)
    })(),
  )
}

export async function applyDeviceAction(
  deviceId: string,
  key: string,
  value?: DeviceStateValue | null,
): Promise<DeviceActionResponse> {
  return trackLoading(
    (async () => {
      const body: { key: string; value?: DeviceStateValue } = { key }
      if (value !== undefined && value !== null) {
        body.value = value
      }
      const response = await apiFetch(
        `${API_DASHBOARD}/devices/${encodeURIComponent(deviceId)}/actions`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        },
      )
      return readJson<DeviceActionResponse>(response)
    })(),
  )
}
