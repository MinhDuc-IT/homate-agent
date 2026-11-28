import { DeviceConnectivity } from '@/components/homemind/DeviceConnectivity'
import { useState } from 'react'
import { DeviceControlList } from './DeviceControlList'
import { useDevices } from '@/context/DevicesContext'
import { formatDeviceStatus, visibleControls } from '@/utils/deviceStatus'
import type { Device, DeviceStateValue } from '@/types/device'

export function SimulationDevicePanel({ device, onClose, onApplied }: { device: Device; onClose: () => void; onApplied: () => void }) {
  const { applyAction, connected } = useDevices()
  const [busy, setBusy] = useState(false)
  async function change(key: string, value: DeviceStateValue) {
    setBusy(true)
    try { await applyAction(device.id, key, value); onApplied() } finally { setBusy(false) }
  }
  return <aside aria-label="Điều khiển thiết bị 3D" className="max-h-72 shrink-0 overflow-y-auto border-t border-[#DCE6DF] bg-white p-4 md:max-h-none md:w-72 md:border-l md:border-t-0">
    <div className="mb-2 flex items-start justify-between gap-3">
      <h2 className="font-semibold text-[#1E4D38]">{device.name}<DeviceConnectivity deviceId={device.id} /></h2>
      <button type="button" aria-label="Đóng điều khiển thiết bị" onClick={onClose} className="rounded px-2 text-xl text-[#66746A]">×</button>
    </div>
    <p className="mb-4 text-sm text-[#66746A]" aria-live="polite">{formatDeviceStatus(device)}</p>
    {!connected && <p role="status" className="mb-3 text-xs text-amber-700">Đang kết nối lại để cập nhật trạng thái…</p>}
    <fieldset disabled={busy} aria-busy={busy} className="disabled:opacity-60">
      <DeviceControlList device={device} controls={visibleControls(device)} theme="green"
        onChange={(key, value) => { void change(key, value) }}
        onAction={(key, sensitive) => {
          if (!sensitive || window.confirm(`Bạn muốn thực hiện thao tác này với ${device.name}?`)) void change(key, true)
        }} />
    </fieldset>
    {busy && <p role="status" className="mt-3 text-xs text-[#66746A]">Đang gửi lệnh…</p>}
  </aside>
}
