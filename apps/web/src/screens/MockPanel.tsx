import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchAmbient, patchRoomMock } from '@/api/ambient'
import { NavRoomIcon } from '@/assets/icons/HomemateIcons'
import { RoomMockRow } from '@/components/homemind/RoomMockRow'
import { WeatherCard } from '@/components/homemind/WeatherCard'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/context/ToastContext'
import type { AmbientSnapshot } from '@/types/ambient'

const TEMP_DEBOUNCE_MS = 400

/** Admin-only tab: mock room occupancy + indoor temperature for the ambient
 * context feature, and preview the cached outdoor weather. */
export function MockPanel() {
  const { showToast } = useToast()
  const [ambient, setAmbient] = useState<AmbientSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [busyRoomId, setBusyRoomId] = useState<string | null>(null)
  const debounceTimers = useRef<Record<string, number>>({})

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchAmbient()
      setAmbient(data)
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Không tải được ngoại cảnh', 'error')
    } finally {
      setLoading(false)
    }
  }, [showToast])

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount once
  }, [])

  async function applyPatch(roomId: string, patch: Parameters<typeof patchRoomMock>[1]) {
    setBusyRoomId(roomId)
    try {
      const updated = await patchRoomMock(roomId, patch)
      setAmbient(updated)
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Không lưu được', 'error')
    } finally {
      setBusyRoomId(null)
    }
  }

  function handleToggleOccupied(roomId: string, occupied: boolean) {
    void applyPatch(roomId, { occupied })
  }

  function handleTempChange(roomId: string, tempC: number) {
    // Optimistic local update so the slider feels smooth while dragging.
    setAmbient((prev) =>
      prev
        ? {
            ...prev,
            rooms: prev.rooms.map((r) =>
              r.id === roomId ? { ...r, indoor_temp_c: tempC } : r,
            ),
          }
        : prev,
    )
    const timers = debounceTimers.current
    if (timers[roomId]) window.clearTimeout(timers[roomId])
    timers[roomId] = window.setTimeout(() => {
      void applyPatch(roomId, { indoor_temp_c: tempC })
    }, TEMP_DEBOUNCE_MS)
  }

  function handleHumidityChange(roomId: string, humidity: number) {
    setAmbient((prev) =>
      prev
        ? {
            ...prev,
            rooms: prev.rooms.map((r) =>
              r.id === roomId ? { ...r, indoor_humidity: humidity } : r,
            ),
          }
        : prev,
    )
    const timerKey = `${roomId}-humidity`
    const timers = debounceTimers.current
    if (timers[timerKey]) window.clearTimeout(timers[timerKey])
    timers[timerKey] = window.setTimeout(() => {
      void applyPatch(roomId, { indoor_humidity: humidity })
    }, TEMP_DEBOUNCE_MS)
  }

  function handleSimulateVacant(roomId: string) {
    void applyPatch(roomId, { vacant_minutes: 30 })
  }

  if (loading && !ambient) {
    return (
      <div className="flex justify-center py-10">
        <LoadingSpinner className="border-[#1E4D38]/30 border-t-[#1E4D38]" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2.5">
      <WeatherCard
        weather={ambient?.weather ?? null}
        localTime={ambient?.local_time ?? ''}
        partOfDay={ambient?.part_of_day ?? ''}
        onRefresh={() => void load()}
        refreshing={loading}
      />

      <div className="rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
        <div className="mb-2 flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-[#E8F5EB] text-[#2E7D32]">
            <NavRoomIcon className="h-3.5 w-3.5" />
          </span>
          <div>
            <h3 className="font-display text-xs font-bold text-[#1C2721]">
              Cảm biến người trong phòng (Dữ liệu mô phỏng)
            </h3>
            <p className="text-[10px] text-[#718076]">
              Thiết lập trạng thái có người và nhiệt độ phòng. Agent sẽ dùng dữ liệu này để tự động đề xuất tiết kiệm điện.
            </p>
          </div>
        </div>

        <div className="mt-2.5 space-y-2">
          {ambient?.rooms.map((room) => (
            <RoomMockRow
              key={room.id}
              room={room}
              busy={busyRoomId === room.id}
              onToggleOccupied={(occupied) => handleToggleOccupied(room.id, occupied)}
              onTempChange={(tempC) => handleTempChange(room.id, tempC)}
              onHumidityChange={(humidity) => handleHumidityChange(room.id, humidity)}
              onSimulateVacant={() => handleSimulateVacant(room.id)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

