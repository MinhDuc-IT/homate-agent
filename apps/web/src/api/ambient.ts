import { API_DASHBOARD } from '@/config/api'
import { apiFetch, readJson } from '@/api/http'
import type {
  AmbientSnapshot,
  AmbientSuggestionResponse,
  RoomMockPatch,
} from '@/types/ambient'
import { trackLoading } from '@/utils/loadingTracker'

export async function fetchAmbient(): Promise<AmbientSnapshot> {
  return trackLoading(
    (async () => {
      const response = await apiFetch(`${API_DASHBOARD}/ambient`)
      return readJson<AmbientSnapshot>(response)
    })(),
  )
}

export async function respondAmbientSuggestion(
  requestId: string,
  approved: boolean,
): Promise<AmbientSuggestionResponse> {
  const response = await apiFetch(
    `${API_DASHBOARD}/ambient/suggestions/${encodeURIComponent(requestId)}/respond`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved }),
    },
  )
  return readJson<AmbientSuggestionResponse>(response)
}

export async function patchRoomMock(
  roomId: string,
  patch: RoomMockPatch,
): Promise<AmbientSnapshot> {
  return trackLoading(
    (async () => {
      const response = await apiFetch(
        `${API_DASHBOARD}/rooms/${encodeURIComponent(roomId)}/mock`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch),
        },
      )
      return readJson<AmbientSnapshot>(response)
    })(),
  )
}
