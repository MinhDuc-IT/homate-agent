import { ToggleSwitch } from '@/components/homemind/ToggleSwitch'
import type { RoomAmbient } from '@/types/ambient'

interface RoomMockRowProps {
  room: RoomAmbient
  busy?: boolean
  onToggleOccupied: (occupied: boolean) => void
  onTempChange: (tempC: number) => void
  onHumidityChange: (humidity: number) => void
  onSimulateVacant: () => void
}

export function RoomMockRow({
  room,
  busy,
  onToggleOccupied,
  onTempChange,
  onHumidityChange,
  onSimulateVacant,
}: RoomMockRowProps) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-[#EEF3EC] bg-[#F8FAF7] p-2.5 transition-colors">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <p className="text-xs font-bold text-[#1C2721]">{room.label}</p>
            <span
              className={`rounded-md px-1.5 py-0.5 text-[9px] font-bold ${
                room.occupied
                  ? 'bg-[#E8F5EB] text-[#2E7D32]'
                  : 'bg-slate-100 text-[#718076]'
              }`}
            >
              {room.occupied ? '● Có người' : '○ Phòng trống'}
            </span>
          </div>
          <p className="mt-0.5 text-[10px] text-[#718076]">
            {!room.occupied ? `Trống ${room.vacant_minutes} phút · ` : ''}
            {room.devices_on.length > 0
              ? `${room.devices_on.length} thiết bị đang bật`
              : 'Tất cả thiết bị đang tắt'}
          </p>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={() => onToggleOccupied(!room.occupied)}
          className="cursor-pointer disabled:opacity-50"
        >
          <ToggleSwitch checked={room.occupied} aria-label={`Có người — ${room.label}`} />
        </button>
      </div>

      <div className="flex items-center gap-2.5 pt-0.5">
        <label
          className="w-20 shrink-0 text-[10px] font-medium text-[#5A6860]"
          htmlFor={`temp-${room.id}`}
        >
          Nhiệt độ phòng:
        </label>
        <input
          id={`temp-${room.id}`}
          type="range"
          min={16}
          max={40}
          step={0.5}
          disabled={busy}
          value={room.indoor_temp_c ?? 28}
          onChange={(event) => onTempChange(Number(event.target.value))}
          className="h-1.5 flex-1 cursor-pointer rounded-lg bg-[#E2EAE0] accent-[#2D6A4F]"
        />
        <span className="w-10 shrink-0 text-right font-mono text-[11px] font-bold text-[#1E4D38]">
          {room.indoor_temp_c != null ? `${room.indoor_temp_c.toFixed(1)}°C` : '—'}
        </span>
      </div>

      <div className="flex items-center gap-2.5 pt-0.5">
        <label
          className="w-20 shrink-0 text-[10px] font-medium text-[#5A6860]"
          htmlFor={`humidity-${room.id}`}
        >
          Độ ẩm phòng:
        </label>
        <input
          id={`humidity-${room.id}`}
          type="range"
          min={0}
          max={100}
          step={1}
          disabled={busy}
          value={room.indoor_humidity ?? 55}
          onChange={(event) => onHumidityChange(Number(event.target.value))}
          className="h-1.5 flex-1 cursor-pointer rounded-lg bg-[#E2EAE0] accent-[#2D6A4F]"
        />
        <span className="w-10 shrink-0 text-right font-mono text-[11px] font-bold text-[#1E4D38]">
          {room.indoor_humidity != null ? `${room.indoor_humidity.toFixed(0)}%` : '—'}
        </span>
      </div>

      <div className="flex justify-end pt-0.5">
        <button
          type="button"
          disabled={busy}
          onClick={onSimulateVacant}
          className="rounded-lg border border-[#D5E5D8] bg-white px-2 py-1 text-[9.5px] font-semibold text-[#1E4D38] transition-colors hover:bg-[#E2EFE5] disabled:opacity-50 cursor-pointer"
        >
          ⏱ Giả lập trống 30 phút
        </button>
      </div>
    </div>
  )
}

