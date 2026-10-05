import { useState } from 'react'
import {
  LeafIcon,
  SparklesIcon,
  SunIcon,
  ZapIcon,
} from '@/assets/icons/HomemateIcons'
import { TabletScreen } from '@/components/layout/TabletScreen'
import { useToast } from '@/context/ToastContext'
import { useEnergy } from '@/hooks/useEnergy'
import type { EnergyPeriod } from '@/types/energy'

function niceAxisMaximum(value: number): number {
  if (value <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(value))
  const normalized = value / magnitude
  const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10
  return step * magnitude
}

function formatAxisValue(value: number): string {
  return value.toLocaleString('vi-VN', {
    maximumFractionDigits: value < 0.1 ? 3 : value < 10 ? 1 : 0,
  })
}

function localDateValue(date = new Date()): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function periodTitle(period: 'week' | 'month' | 'quarter' | 'year', anchor: string): string {
  const [year, month, day] = anchor.split('-').map(Number)
  if (period === 'year') return `Năm ${year}`
  if (period === 'month') return `Tháng ${String(month).padStart(2, '0')}/${year}`
  if (period === 'quarter') return `Quý ${Math.floor((month - 1) / 3) + 1}/${year}`
  const date = new Date(year, month - 1, day)
  const mondayOffset = (date.getDay() + 6) % 7
  const start = new Date(year, month - 1, day - mondayOffset)
  const end = new Date(start)
  end.setDate(start.getDate() + 6)
  return `${String(start.getDate()).padStart(2, '0')}/${String(start.getMonth() + 1).padStart(2, '0')}–${String(end.getDate()).padStart(2, '0')}/${String(end.getMonth() + 1).padStart(2, '0')}`
}

function formatCurrency(value: number | null | undefined, currency: string | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: currency || 'VND',
    maximumFractionDigits: 0,
  }).format(value)
}

export function EnergyScreen() {
  const { showToast } = useToast()
  const [periodTab, setPeriodTab] = useState<'week' | 'month' | 'quarter' | 'year'>('month')
  const [anchorDate, setAnchorDate] = useState(() => localDateValue())
  const [hoveredBar, setHoveredBar] = useState<number | null>(null)
  const period: EnergyPeriod = periodTab === 'quarter' ? '3months' : periodTab
  const { data, loading, error } = useEnergy(period, { anchor: anchorDate })
  const colors = ['#2D6A4F', '#40916C', '#E9C46A', '#F4A261', '#A855F7']
  const total = data?.total_kwh ?? 0
  const changePercent = data?.change_percent
  const sourceLabel = data?.source === 'measured'
    ? 'Đo thực tế'
    : data?.source === 'mixed'
      ? `Hỗn hợp · ${Math.round(data.measurement_coverage * 100)}% đo thật`
      : 'Ước tính'
  const dailyTrend = (data?.timeseries ?? []).map((item) => ({
    date: period === 'year'
      ? `T${item.bucket.slice(5, 7)}`
      : period === '3months'
        ? `T${item.bucket.split('-W')[1] ?? item.bucket}`
        : item.bucket.slice(5, 10),
    kwh: item.kwh,
  }))
  const devicePieData = (data?.by_device ?? []).slice(0, 5).map((item, index) => ({
    ...item,
    percent: total > 0 ? Math.round(item.kwh / total * 100) : 0,
    color: colors[index],
  }))
  const roomMax = Math.max(0, ...(data?.by_room ?? []).map((item) => item.kwh))
  const roomComparison = (data?.by_room ?? []).map((item) => ({
    ...item,
    percent: roomMax > 0 ? item.kwh / roomMax * 100 : 0,
  }))
  const maxTrend = Math.max(0, ...dailyTrend.map((item) => item.kwh))
  const trendAxisMax = niceAxisMaximum(maxTrend)
  const trendAxisTicks = [trendAxisMax, trendAxisMax / 2, 0]
  const topDevice = devicePieData[0]
  let pieCursor = 0
  const pieStops = devicePieData.map((item) => {
    const start = pieCursor
    pieCursor = Math.min(100, pieCursor + (total > 0 ? item.kwh / total * 100 : 0))
    return `${item.color} ${start}% ${pieCursor}%`
  })
  if (pieCursor < 100) pieStops.push(`#E6ECE3 ${pieCursor}% 100%`)
  const devicePieBackground = total > 0
    ? `conic-gradient(${pieStops.join(', ')})`
    : '#E6ECE3'

  const periodTabs = [
    { id: 'week' as const, label: 'Tuần' },
    { id: 'month' as const, label: 'Tháng' },
    { id: 'quarter' as const, label: 'Quý' },
    { id: 'year' as const, label: 'Năm' },
  ]

  const shiftPeriod = (direction: -1 | 1) => {
    const [year, month, day] = anchorDate.split('-').map(Number)
    const next = new Date(year, month - 1, day)
    if (periodTab === 'week') next.setDate(next.getDate() + direction * 7)
    if (periodTab === 'month') {
      next.setDate(1)
      next.setMonth(next.getMonth() + direction)
    }
    if (periodTab === 'quarter') {
      next.setDate(1)
      next.setMonth(next.getMonth() + direction * 3)
    }
    if (periodTab === 'year') {
      next.setDate(1)
      next.setMonth(0)
      next.setFullYear(next.getFullYear() + direction)
    }
    setAnchorDate(localDateValue(next))
  }

  return (
    <TabletScreen>
      <div className="flex h-full min-h-0 flex-col gap-2.5">
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1 rounded-xl border border-[#E6ECE3] bg-white p-1 shadow-xs">
            {periodTabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setPeriodTab(tab.id)}
                className={`rounded-lg px-3 py-1 text-[10px] font-semibold transition ${
                  periodTab === tab.id
                    ? 'bg-[#E2EFE5] text-[#1E4D38]'
                    : 'text-[#5A6860] hover:bg-[#F4F6F3]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="ml-auto flex items-center gap-2 rounded-xl border border-[#E6ECE3] bg-white px-3 py-1 text-[10px] font-bold text-[#1C2721] shadow-xs">
            <button type="button" className="text-gray-400 hover:text-[#1E4D38]" onClick={() => shiftPeriod(-1)} aria-label="Kỳ trước">‹</button>
            {periodTab === 'week' ? (
              <input type="date" value={anchorDate} onChange={(event) => event.target.value && setAnchorDate(event.target.value)} className="bg-transparent outline-none" aria-label="Chọn tuần theo ngày" />
            ) : periodTab === 'year' ? (
              <input
                type="number"
                min="2020"
                max="2100"
                value={anchorDate.slice(0, 4)}
                onChange={(event) => /^\d{4}$/.test(event.target.value) && setAnchorDate(`${event.target.value}-${anchorDate.slice(5)}`)}
                className="w-14 bg-transparent text-center outline-none"
                aria-label="Chọn năm"
              />
            ) : (
              <input type="month" value={anchorDate.slice(0, 7)} onChange={(event) => event.target.value && setAnchorDate(`${event.target.value}-01`)} className="bg-transparent outline-none" aria-label={periodTab === 'quarter' ? 'Chọn quý theo tháng' : 'Chọn tháng'} />
            )}
            <button type="button" className="text-gray-400 hover:text-[#1E4D38]" onClick={() => shiftPeriod(1)} aria-label="Kỳ sau">›</button>
          </div>
        </div>
        {error ? <p className="shrink-0 text-[10px] text-red-600">{error}</p> : null}
        <div className="grid min-h-0 flex-1 grid-rows-[auto_minmax(0,1fr)_minmax(0,0.9fr)] gap-2.5">
        {/* KPI row */}
        <div className="grid shrink-0 grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
          <div className="rounded-2xl border border-[#E6ECE3] bg-white p-2.5 shadow-xs">
            <p className="text-[10px] font-semibold text-[#718076]">{periodTitle(periodTab, anchorDate)}</p>
            <div className="mt-1 flex items-baseline gap-1">
              <ZapIcon className="h-4 w-4 text-[#2D6A4F]" />
              <span className="font-display text-lg font-extrabold text-[#1C2721]">
                {loading ? '…' : total.toFixed(2)}
              </span>
              <span className="text-[10px] text-[#718076]">kWh</span>
            </div>
          </div>
          <div className="rounded-2xl border border-[#E6ECE3] bg-white p-2.5 shadow-xs">
            <p className="text-[10px] font-semibold text-[#718076]">
              So với kỳ trước
            </p>
            <p className={`mt-1 font-display text-lg font-extrabold ${
              changePercent == null ? 'text-[#718076]' : changePercent <= 0 ? 'text-[#22C55E]' : 'text-[#E76F51]'
            }`}>
              {loading ? '…' : changePercent == null
                ? '—'
                : `${changePercent > 0 ? '↑' : changePercent < 0 ? '↓' : '→'} ${Math.abs(changePercent).toFixed(1)}%`}
            </p>
          </div>
          <div className="rounded-2xl border border-[#E6ECE3] bg-white p-2.5 shadow-xs">
            <p className="text-[10px] font-semibold text-[#718076]">
              Chi phí ước tính
            </p>
            <p className="mt-1 font-display text-lg font-extrabold text-[#1C2721]">
              {loading ? '…' : formatCurrency(data?.estimated_cost, data?.currency)}
            </p>
          </div>
          <div className="rounded-2xl border border-[#E6ECE3] bg-white p-2.5 shadow-xs">
            <p className="text-[10px] font-semibold text-[#718076]">Nguồn dữ liệu</p>
            <p className="mt-1 font-display text-base font-extrabold text-[#1C2721]">
              {loading ? '…' : sourceLabel}
            </p>
          </div>
          <div className="col-span-2 flex flex-col justify-between rounded-2xl border border-[#D5E5D8] bg-[#EAF5ED] p-2.5 text-[10px] sm:col-span-1">
            <div className="flex items-center gap-1 font-bold text-[#1E4D38]">
              <SparklesIcon className="h-3.5 w-3.5 text-[#2D6A4F]" />
              <span>Gợi ý thông minh</span>
            </div>
            <p className="mt-1 leading-snug text-[#3B4D42]">
              {topDevice ? `${topDevice.name} đang chiếm ${topDevice.percent}% điện năng trong kỳ.` : 'Chưa có đủ dữ liệu để đưa ra gợi ý.'}
            </p>
            <button
              type="button"
              onClick={() =>
                showToast('Đã mở phân tích tối ưu chi tiết', 'info')
              }
              className="mt-1 text-left text-[9px] font-bold text-[#1E4D38] hover:underline"
            >
              Xem chi tiết →
            </button>
          </div>
        </div>

        {/* Charts row */}
        <div className="grid min-h-0 grid-cols-1 gap-2.5 lg:grid-cols-12">
          <div className="flex min-h-0 flex-col rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm lg:col-span-7">
            <div className="mb-2 flex shrink-0 items-center justify-between">
              <h3 className="font-display text-xs font-bold text-[#1C2721]">
                Xu hướng tiêu thụ điện
              </h3>
              <span className="text-[9px] text-[#88968E]">kWh</span>
            </div>
            <div className="flex min-h-0 flex-1 items-end gap-2 pb-1">
              <div className="flex h-full flex-col justify-between text-right text-[8px] text-[#88968E]">
                {trendAxisTicks.map((tick) => (
                  <span key={tick}>{formatAxisValue(tick)}</span>
                ))}
              </div>
              <div className="relative flex h-full flex-1 items-end justify-between gap-1 border-b border-[#E6ECE3]">
                {dailyTrend.map((item, idx) => {
                  const heightPercent = (item.kwh / trendAxisMax) * 100
                  const isHovered = hoveredBar === idx
                  return (
                    <div
                      key={item.date}
                      className="relative flex h-full flex-1 flex-col items-center justify-end"
                      onMouseEnter={() => setHoveredBar(idx)}
                      onMouseLeave={() => setHoveredBar(null)}
                    >
                      <div
                        className={`relative w-full max-w-[28px] rounded-t-sm transition-all ${
                          isHovered
                            ? 'bg-[#1E4D38]'
                            : 'bg-[#52B788] hover:bg-[#2D6A4F]'
                        }`}
                        style={{ height: `${heightPercent}%` }}
                      >
                        {isHovered && (
                          <div className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-1 flex -translate-x-1/2 flex-col items-center whitespace-nowrap rounded-md bg-white px-1.5 py-1 text-[8px] shadow-md ring-1 ring-black/5">
                            <span className="font-medium text-[#718076]">{item.date}</span>
                            <span className="font-bold text-[#1C2721]">
                              {item.kwh.toLocaleString('vi-VN', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              })} kWh
                            </span>
                          </div>
                        )}
                      </div>
                      <span className="mt-1 text-[8px] text-[#718076]">
                        {item.date}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          <div className="flex min-h-0 flex-col rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm lg:col-span-5">
            <h3 className="shrink-0 font-display text-xs font-bold text-[#1C2721]">
              Thiết bị tiêu thụ nhiều nhất
            </h3>
            <div className="mt-2 flex min-h-0 flex-1 items-center gap-3">
              <div
                className="relative flex h-24 w-24 shrink-0 items-center justify-center rounded-full"
                style={{ background: devicePieBackground }}
              >
                <div className="absolute inset-[14px] rounded-full bg-white" />
                <div className="relative z-10 text-center">
                  <p className="text-[8px] text-[#718076]">Tổng</p>
                  <p className="font-display text-[10px] font-bold text-[#1C2721]">
                    {total.toFixed(2)} kWh
                  </p>
                </div>
              </div>
              <div className="min-h-0 flex-1 space-y-1 overflow-y-auto text-[10px]">
                {devicePieData.map((d) => (
                  <div key={d.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{ backgroundColor: d.color }}
                      />
                      <span className="text-[#1C2721]">{d.name}</span>
                    </div>
                    <span className="font-semibold text-[#718076]">
                      {d.kwh.toFixed(2)} kWh · {d.percent}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Bottom row */}
        <div className="grid min-h-0 grid-cols-1 gap-2.5 lg:grid-cols-12">
          <div className="flex min-h-0 flex-col rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm lg:col-span-6">
            <div className="mb-2 flex shrink-0 items-center justify-between">
              <h3 className="font-display text-xs font-bold text-[#1C2721]">
                So sánh theo phòng
              </h3>
              <span className="text-[9px] text-[#88968E]">{periodTitle(periodTab, anchorDate)}</span>
            </div>
            <div className="min-h-0 flex-1 space-y-2 overflow-y-auto text-[10px]">
              {roomComparison.map((r) => (
                <div key={r.name} className="space-y-1">
                  <div className="flex items-center justify-between font-medium text-[#1C2721]">
                    <span>
                      {r.name}
                    </span>
                    <span className="font-bold">{r.kwh.toFixed(2)} kWh</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#EDF2EB]">
                    <div
                      className="h-full rounded-full bg-[#2D6A4F]"
                      style={{ width: `${r.percent}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="relative flex min-h-0 flex-col overflow-hidden rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm lg:col-span-6">
            <h3 className="shrink-0 font-display text-xs font-bold text-[#1C2721]">
              Nhận định từ{' '}
              <span className="text-[#1E4D38]">HomeMate AI</span>
            </h3>
            <div className="mt-2 min-h-0 flex-1 space-y-2 overflow-y-auto text-[10px]">
              {[
                {
                  icon: <SunIcon className="h-3.5 w-3.5" />,
                  bg: 'bg-amber-100 text-amber-600',
                  title: 'Tiêu thụ tăng vào buổi tối',
                  desc: 'Mức tiêu thụ điện thường tăng cao từ 19:00 – 22:00.',
                },
                {
                  icon: <SparklesIcon className="h-3.5 w-3.5" />,
                  bg: 'bg-[#E2EFE5] text-[#1E4D38]',
                  title: topDevice ? `${topDevice.name} tiêu thụ nhiều nhất` : 'Chưa đủ dữ liệu thiết bị',
                  desc: topDevice ? `Thiết bị này chiếm ${topDevice.percent}% tổng điện năng trong kỳ.` : 'Hệ thống sẽ phân tích khi có dữ liệu.',
                },
                {
                  icon: <LeafIcon className="h-3.5 w-3.5" />,
                  bg: 'bg-[#E8F5EB] text-[#2E7D32]',
                  title: 'Bạn đang tiết kiệm tốt!',
                  desc: 'Tổng điện tuần này giảm 9% so với tuần trước.',
                },
              ].map((insight) => (
                <div key={insight.title} className="flex items-start gap-2">
                  <span
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md ${insight.bg}`}
                  >
                    {insight.icon}
                  </span>
                  <div>
                    <p className="font-bold text-[#1C2721]">{insight.title}</p>
                    <p className="mt-0.5 leading-relaxed text-[#718076]">
                      {insight.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        </div>
      </div>
    </TabletScreen>
  )
}
