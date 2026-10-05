import { SunIcon } from '@/assets/icons/HomemateIcons'
import type { WeatherSnapshot } from '@/types/ambient'

interface WeatherCardProps {
  weather: WeatherSnapshot | null
  localTime: string
  partOfDay: string
  onRefresh: () => void
  refreshing?: boolean
}

const PART_OF_DAY_LABEL: Record<string, string> = {
  morning: 'Buổi sáng',
  noon: 'Buổi trưa',
  afternoon: 'Buổi chiều',
  evening: 'Buổi tối',
  night: 'Ban đêm',
}

export function WeatherCard({
  weather,
  localTime,
  partOfDay,
  onRefresh,
  refreshing,
}: WeatherCardProps) {
  return (
    <div className="rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-[#E8F5EB] text-[#2E7D32]">
            <SunIcon className="h-3.5 w-3.5" />
          </span>
          <h3 className="font-display text-xs font-bold text-[#1C2721]">
            Ngoại cảnh & Thời tiết
          </h3>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          className="flex items-center gap-1 rounded-lg border border-[#D5E5D8] bg-[#F8FAF7] px-2.5 py-1 text-[10px] font-bold text-[#1E4D38] transition-colors hover:bg-[#E2EFE5] disabled:opacity-50"
        >
          <span>↻</span>
          <span>{refreshing ? 'Đang làm mới…' : 'Làm mới'}</span>
        </button>
      </div>

      {!weather ? (
        <p className="text-[10px] text-[#88968E]">
          Chưa cấu hình WEATHER_API_KEY hoặc API đang lỗi — agent sẽ bỏ qua ngoại cảnh này.
        </p>
      ) : (
        <div className="flex items-center justify-between gap-3 rounded-xl border border-[#EEF3EC] bg-[#F8FAF7] p-2.5">
          <div>
            <div className="flex items-baseline gap-2">
              <span className="font-display text-xl font-bold text-[#1C2721]">
                {weather.temp_c.toFixed(0)}°C
              </span>
              <span className="text-[11px] font-medium text-[#718076]">
                cảm giác {weather.feels_like_c.toFixed(0)}°C
              </span>
            </div>
            <p className="mt-0.5 text-[10px] text-[#5A6860]">
              <span className="font-semibold text-[#1C2721]">{weather.description || weather.condition || '—'}</span>
              {' · '}
              <span>Độ ẩm {weather.humidity}%</span>
              {weather.stale ? (
                <span className="ml-1.5 rounded-md bg-amber-100 px-1 py-0.2 text-[9px] font-bold text-amber-700">
                  dữ liệu cũ
                </span>
              ) : null}
            </p>
          </div>
          <div className="text-right">
            <span className="inline-block rounded-md bg-[#E8F5EB] px-2 py-0.5 text-[10px] font-bold text-[#2E7D32]">
              {PART_OF_DAY_LABEL[partOfDay] ?? partOfDay}
            </span>
            <p className="mt-0.5 font-mono text-[11px] font-bold text-[#1C2721]">
              {localTime || '—'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

