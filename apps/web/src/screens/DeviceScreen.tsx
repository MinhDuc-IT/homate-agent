import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { PowerIcon, StarIcon } from '@/assets/icons/HomemateIcons'
import {
  BulbIcon,
  CameraIcon,
  CurtainIcon,
  DropletIcon,
  FanIcon,
  FlameIcon,
  LockIcon,
  PlugIcon,
  SnowflakeIcon,
  SpeakerIcon,
  TvIcon,
} from '@/assets/icons/HomeMindIcons'
import { DeviceControlList } from '@/components/homemind/DeviceControlList'
import { TabletScreen } from '@/components/layout/TabletScreen'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useDevices } from '@/context/DevicesContext'
import { useSession } from '@/context/SessionContext'
import { useToast } from '@/context/ToastContext'
import { useEnergy } from '@/hooks/useEnergy'
import type { Device, DeviceIconKind, DeviceStateValue } from '@/types/device'
import {
  formatDeviceStatus,
  isDeviceActive,
  visibleControls,
} from '@/utils/deviceStatus'

const TYPE_FILTERS: { value: string; label: string }[] = [
  { value: 'all', label: 'Tất cả' },
  { value: 'climate', label: 'Điều hòa & Không khí' },
  { value: 'light', label: 'Chiếu sáng' },
  { value: 'fan', label: 'Quạt' },
  { value: 'plug', label: 'Ổ cắm' },
  { value: 'security', label: 'An ninh' },
]

function deviceIcon(
  kind: DeviceIconKind,
  className = 'h-3.5 w-3.5',
): ReactNode {
  switch (kind) {
    case 'bulb':
      return <BulbIcon className={className} />
    case 'snowflake':
      return <SnowflakeIcon className={className} />
    case 'flame':
      return <FlameIcon className={className} />
    case 'lock':
      return <LockIcon className={className} />
    case 'curtain':
      return <CurtainIcon className={className} />
    case 'speaker':
      return <SpeakerIcon className={className} />
    case 'tv':
      return <TvIcon className={className} />
    case 'fan':
      return <FanIcon className={className} />
    case 'plug':
      return <PlugIcon className={className} />
    case 'camera':
      return <CameraIcon className={className} />
    case 'droplet':
      return <DropletIcon className={className} />
  }
}

function matchesTypeFilter(kind: DeviceIconKind, filterType: string): boolean {
  if (filterType === 'all') return true
  const groups: Record<string, DeviceIconKind[]> = {
    climate: ['snowflake', 'flame', 'droplet'],
    light: ['bulb'],
    fan: ['fan'],
    plug: ['plug'],
    security: ['lock', 'camera'],
  }
  return groups[filterType]?.includes(kind) ?? false
}

function deviceHeroImage(device: Device): string | null {
  if (device.kind === 'snowflake') return '/assets/images/ac_unit.png'
  return null
}

function formatDuration(minutes: number): string {
  const rounded = Math.max(0, Math.floor(minutes))
  const hours = Math.floor(rounded / 60)
  const remainder = rounded % 60
  if (hours === 0) return `${remainder} phút`
  if (remainder === 0) return `${hours} giờ`
  return `${hours} giờ ${remainder} phút`
}

export function DeviceScreen() {
  const { showToast } = useToast()
  const { rooms } = useSession()
  const { devices, loading, error, applyAction } = useDevices()
  const { data: todayEnergy } = useEnergy('today')

  const [selectedRoom, setSelectedRoom] = useState('all')
  const [selectedType, setSelectedType] = useState('all')
  const [selectedStatus, setSelectedStatus] = useState('all')
  const [onlyFavorites, setOnlyFavorites] = useState(false)
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null)
  const [favorites, setFavorites] = useState<Record<string, boolean>>({
    'ac-living': true,
    'light-living': true,
    'fan-bed': true,
  })

  const roomLabelById = useMemo(
    () => Object.fromEntries(rooms.map((r) => [r.id, r.label])),
    [rooms],
  )

  const filteredDevices = useMemo(() => {
    return devices.filter((device) => {
      if (selectedRoom !== 'all' && device.room !== selectedRoom) return false
      if (!matchesTypeFilter(device.kind, selectedType)) return false
      const active = isDeviceActive(device)
      if (selectedStatus === 'on' && !active) return false
      if (selectedStatus === 'off' && active) return false
      if (onlyFavorites && !favorites[device.id]) return false
      return true
    })
  }, [
    devices,
    selectedRoom,
    selectedType,
    selectedStatus,
    onlyFavorites,
    favorites,
  ])

  const selectedDevice =
    devices.find((d) => d.id === selectedDeviceId) ??
    filteredDevices[0] ??
    devices[0] ??
    null

  useEffect(() => {
    if (!devices.length) {
      setSelectedDeviceId(null)
      return
    }
    if (!selectedDeviceId || !devices.some((d) => d.id === selectedDeviceId)) {
      setSelectedDeviceId(devices[0].id)
    }
  }, [devices, selectedDeviceId])

  const quickDevices = useMemo(() => {
    const favIds = Object.entries(favorites)
      .filter(([, on]) => on)
      .map(([id]) => id)
    const favDevices = favIds
      .map((id) => devices.find((d) => d.id === id))
      .filter((d): d is Device => Boolean(d))
    const extras = devices.filter((d) => !favIds.includes(d.id))
    return [...favDevices, ...extras].slice(0, 4)
  }, [devices, favorites])

  const toggleFavorite = (id: string) => {
    setFavorites((prev) => {
      const next = !prev[id]
      showToast(
        next ? 'Đã thêm vào mục yêu thích' : 'Đã bỏ khỏi mục yêu thích',
        'info',
      )
      return { ...prev, [id]: next }
    })
  }

  const updateDevice = async (
    deviceId: string,
    key: string,
    value?: DeviceStateValue,
  ) => {
    await applyAction(deviceId, key, value)
  }

  const handleAction = (device: Device, key: string, sensitive?: boolean) => {
    if (sensitive || key === 'unlock') {
      if (!window.confirm(`Xác nhận thao tác ${key} với ${device.name}?`)) return
    }
    void applyAction(device.id, key).then((updated) => {
      if (updated) showToast(`${device.name}: ${key}`, 'info')
    })
  }

  const handlePowerToggle = () => {
    if (!selectedDevice) return
    const powerControl = selectedDevice.controls.find(
      (c) => c.type === 'toggle' && c.key === 'power',
    )
    if (!powerControl) return
    const next = !selectedDevice.state.power
    void updateDevice(selectedDevice.id, 'power', next)
    showToast(
      `${selectedDevice.name}: ${next ? 'Đã bật' : 'Đã tắt'}`,
      next ? 'success' : 'info',
    )
  }

  const selectedActive = selectedDevice ? isDeviceActive(selectedDevice) : false
  const selectedEnergy = selectedDevice
    ? todayEnergy?.by_device.find((item) => item.id === selectedDevice.id)
    : undefined
  const selectedEnergyKwh = selectedEnergy?.kwh ?? 0
  const selectedCurrentPowerW = selectedEnergy?.current_power_w ?? 0
  const selectedActiveMinutesToday = selectedEnergy?.active_minutes_today ?? 0
  const selectedCurrentSessionMinutes = selectedEnergy?.current_session_minutes ?? 0
  const hasPowerToggle = selectedDevice?.controls.some(
    (c) => c.type === 'toggle' && c.key === 'power',
  )

  return (
    <TabletScreen>
      <div className="flex h-full min-h-0 flex-col gap-2">
        <div className="flex shrink-0 flex-wrap items-center gap-2 rounded-xl border border-[#E6ECE3] bg-white p-2 shadow-xs text-[10px]">
          <div className="flex items-center gap-1">
            <span className="text-[#718076]">Phòng</span>
            <select
              value={selectedRoom}
              onChange={(e) => setSelectedRoom(e.target.value)}
              className="rounded-md border border-[#E0E7DE] bg-[#F8FAF7] px-1.5 py-1 font-medium text-[#1C2721] outline-none"
            >
              <option value="all">Tất cả</option>
              {rooms.map((room) => (
                <option key={room.id} value={room.id}>
                  {room.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-[#718076]">Loại thiết bị</span>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="rounded-md border border-[#E0E7DE] bg-[#F8FAF7] px-1.5 py-1 font-medium text-[#1C2721] outline-none"
            >
              {TYPE_FILTERS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-[#718076]">Trạng thái</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="rounded-md border border-[#E0E7DE] bg-[#F8FAF7] px-1.5 py-1 font-medium text-[#1C2721] outline-none"
            >
              <option value="all">Tất cả</option>
              <option value="on">Đang bật</option>
              <option value="off">Đang tắt</option>
            </select>
          </div>
          <label className="ml-auto flex cursor-pointer items-center gap-1.5 font-medium text-[#5A6860]">
            <input
              type="checkbox"
              checked={onlyFavorites}
              onChange={(e) => setOnlyFavorites(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-[#D5E5D8] text-[#1E4D38] focus:ring-[#1E4D38]"
            />
            <span>Yêu thích</span>
          </label>
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-1 gap-2 lg:grid-cols-12">
          <div className="flex min-h-0 flex-col gap-2 lg:col-span-7">
            <div className="shrink-0">
              <h3 className="font-display text-xs font-bold text-[#1C2721]">
                Thiết bị thường dùng
              </h3>
              <div className="mt-1.5 grid grid-cols-2 gap-1.5 sm:grid-cols-4">
                {quickDevices.map((device) => {
                  const hero = deviceHeroImage(device)
                  const active = isDeviceActive(device)
                  return (
                    <button
                      key={device.id}
                      type="button"
                      onClick={() => setSelectedDeviceId(device.id)}
                      className={`rounded-xl p-2 text-left transition ${
                        selectedDevice?.id === device.id
                          ? 'border-2 border-[#1E4D38] bg-[#EAF4EC]'
                          : 'border border-[#E6ECE3] bg-white hover:bg-[#F8FAF7]'
                      }`}
                    >
                      {hero ? (
                        <div className="h-7 overflow-hidden">
                          <img
                            src={hero}
                            alt=""
                            className="h-full object-contain"
                          />
                        </div>
                      ) : (
                        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#F4F6F3] text-[#1E4D38]">
                          {deviceIcon(device.kind)}
                        </div>
                      )}
                      <p className="mt-1 truncate text-[10px] font-bold text-[#1C2721]">
                        {device.name}
                      </p>
                      <p
                        className={`truncate text-[9px] ${
                          active ? 'text-[#22C55E]' : 'text-[#718076]'
                        }`}
                      >
                        {formatDeviceStatus(device)}
                      </p>
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
              <h3 className="shrink-0 font-display text-xs font-bold text-[#1C2721]">
                Tất cả thiết bị ({filteredDevices.length})
              </h3>

              {loading && devices.length === 0 ? (
                <div className="flex flex-1 items-center justify-center py-6">
                  <LoadingSpinner />
                </div>
              ) : (
                <div className="mt-1.5 min-h-0 flex-1 divide-y divide-[#F0F4EE] overflow-y-auto text-[10px]">
                  {filteredDevices.map((device) => {
                    const active = isDeviceActive(device)
                    const energy = todayEnergy?.by_device.find((item) => item.id === device.id)
                    const energyKwh = energy?.kwh ?? 0
                    const currentPowerW = energy?.current_power_w ?? 0
                    const isFav = favorites[device.id]
                    const isSelected = selectedDevice?.id === device.id
                    return (
                      <div
                        key={device.id}
                        onClick={() => setSelectedDeviceId(device.id)}
                        className={`flex cursor-pointer items-center justify-between py-2 transition hover:bg-[#F8FAF7] ${
                          isSelected ? 'rounded-lg bg-[#F4FAF5] px-1.5' : ''
                        }`}
                      >
                        <div className="flex min-w-0 items-center gap-2">
                          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#F2F6F0] text-[#1E4D38]">
                            {deviceIcon(device.kind)}
                          </span>
                          <div className="min-w-0">
                            <p className="truncate font-bold text-[#1C2721]">
                              {device.name}
                            </p>
                            <p className="truncate text-[9px] text-[#718076]">
                              {roomLabelById[device.room] ?? device.room}
                            </p>
                          </div>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <div className="text-right">
                            <p
                              className={`font-semibold ${
                                active ? 'text-[#22C55E]' : 'text-[#88968E]'
                              }`}
                            >
                              {formatDeviceStatus(device)}
                            </p>
                            <p className="text-[8px] text-[#88968E]">
                              {currentPowerW.toLocaleString('vi-VN', { maximumFractionDigits: 1 })} W · Hôm nay {energyKwh.toFixed(2)} kWh
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              toggleFavorite(device.id)
                            }}
                            className="text-[#D5E5D8] hover:text-[#2D6A4F]"
                          >
                            <StarIcon
                              filled={isFav}
                              className={
                                isFav
                                  ? 'h-3.5 w-3.5 fill-[#2D6A4F] text-[#2D6A4F]'
                                  : 'h-3.5 w-3.5 text-[#D5E5D8]'
                              }
                            />
                          </button>
                          <span className="text-[#A8B5AD]">›</span>
                        </div>
                      </div>
                    )
                  })}
                  {!loading && filteredDevices.length === 0 ? (
                    <p className="py-6 text-center text-[10px] text-[#88968E]">
                      {error
                        ? 'Không tải được thiết bị. Kiểm tra backend đang chạy.'
                        : 'Không có thiết bị phù hợp bộ lọc.'}
                    </p>
                  ) : null}
                </div>
              )}
            </div>
          </div>

          <div className="min-h-0 lg:col-span-5">
            <div className="flex h-full min-h-0 flex-col overflow-y-auto rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
              {!selectedDevice ? (
                <p className="text-[10px] text-[#88968E]">
                  Chọn thiết bị để xem chi tiết.
                </p>
              ) : (
                <>
                  <div className="flex shrink-0 items-center justify-between">
                    <div className="min-w-0">
                      <h3 className="truncate font-display text-xs font-bold text-[#1C2721]">
                        {selectedDevice.name}
                      </h3>
                      <p className="text-[10px] text-[#718076]">
                        {roomLabelById[selectedDevice.room] ??
                          selectedDevice.room}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => toggleFavorite(selectedDevice.id)}
                        className="text-[#2D6A4F]"
                      >
                        <StarIcon
                          filled={favorites[selectedDevice.id]}
                          className={
                            favorites[selectedDevice.id]
                              ? 'h-4 w-4 fill-[#2D6A4F] text-[#2D6A4F]'
                              : 'h-4 w-4 text-[#D5E5D8]'
                          }
                        />
                      </button>
                    </div>
                  </div>

                  {deviceHeroImage(selectedDevice) ? (
                    <div className="my-2 flex h-20 shrink-0 items-center justify-center rounded-xl bg-[#FAFCF9] p-2">
                      <img
                        src={deviceHeroImage(selectedDevice)!}
                        alt={selectedDevice.name}
                        className="max-h-full object-contain"
                      />
                    </div>
                  ) : (
                    <div className="my-2 flex h-16 shrink-0 items-center justify-center rounded-xl bg-[#FAFCF9] text-[#1E4D38]">
                      {deviceIcon(selectedDevice.kind, 'h-8 w-8')}
                    </div>
                  )}

                  {hasPowerToggle ? (
                    <div className="flex shrink-0 items-center justify-between rounded-xl bg-[#F8FAF7] px-3 py-2">
                      <span className="text-[10px] font-semibold text-[#5A6860]">
                        Trạng thái
                      </span>
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[10px] font-bold ${
                            selectedActive
                              ? 'text-[#22C55E]'
                              : 'text-[#A8B5AD]'
                          }`}
                        >
                          {selectedActive ? 'Bật' : 'Tắt'}
                        </span>
                        <button
                          type="button"
                          onClick={handlePowerToggle}
                          aria-label={selectedActive ? 'Tắt thiết bị' : 'Bật thiết bị'}
                          className={`flex h-7 w-7 items-center justify-center rounded-full text-white transition ${
                            selectedActive
                              ? 'bg-[#2D6A4F] hover:bg-[#1E4D38]'
                              : 'bg-[#CBD5CE] hover:bg-[#A8B5AD]'
                          }`}
                        >
                          <PowerIcon className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="shrink-0 rounded-xl bg-[#F8FAF7] px-3 py-2 text-[10px] text-[#5A6860]">
                      {formatDeviceStatus(selectedDevice)}
                    </div>
                  )}

                  <div className="mt-2 min-h-0 flex-1">
                    {visibleControls(selectedDevice).length > 0 ? (
                      <DeviceControlList
                        device={selectedDevice}
                        controls={visibleControls(selectedDevice)}
                        theme="green"
                        onChange={(key, value) => {
                          void updateDevice(selectedDevice.id, key, value)
                        }}
                        onAction={(key, sensitive) => {
                          handleAction(selectedDevice, key, sensitive)
                        }}
                      />
                    ) : (
                      <p className="text-[10px] text-[#88968E]">
                        Thiết bị không có điều khiển trực tiếp.
                      </p>
                    )}
                  </div>

                  <div className="mt-2 grid shrink-0 grid-cols-2 gap-1.5 text-[10px]">
                    <div className="rounded-lg bg-[#F8FAF7] p-2">
                      <p className="text-[9px] text-[#718076]">
                        Công suất hiện tại
                      </p>
                      <p className="font-display text-sm font-bold text-[#1C2721]">
                        {selectedCurrentPowerW.toLocaleString('vi-VN', { maximumFractionDigits: 1 })}{' '}
                        <span className="text-[9px] font-normal">W</span>
                      </p>
                    </div>
                    <div className="rounded-lg bg-[#F8FAF7] p-2">
                      <p className="text-[9px] text-[#718076]">
                        Tiêu thụ hôm nay
                      </p>
                      <p className="font-display text-sm font-bold text-[#1C2721]">
                        {selectedEnergyKwh.toFixed(2)}{' '}
                        <span className="text-[9px] font-normal">kWh</span>
                      </p>
                    </div>
                    <div className="rounded-lg bg-[#F8FAF7] p-2">
                      <p className="text-[9px] text-[#718076]">
                        Hoạt động hôm nay
                      </p>
                      <p className="font-display text-sm font-bold text-[#1C2721]">
                        {formatDuration(selectedActiveMinutesToday)}
                      </p>
                    </div>
                    <div className="rounded-lg bg-[#F8FAF7] p-2">
                      <p className="text-[9px] text-[#718076]">
                        Phiên hiện tại
                      </p>
                      <p className="font-display text-sm font-bold text-[#1C2721]">
                        {selectedCurrentSessionMinutes > 0
                          ? formatDuration(selectedCurrentSessionMinutes)
                          : 'Không hoạt động'}
                      </p>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </TabletScreen>
  )
}
