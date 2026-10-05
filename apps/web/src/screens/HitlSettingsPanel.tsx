import { useEffect, useMemo, useState } from 'react'
import {
  fetchHitlPolicies,
  fetchHomeSettings,
  patchHomeSettings,
  replaceHitlPolicies,
  type HitlPolicyWrite,
} from '@/api/settings'
import { useDevices } from '@/context/DevicesContext'
import { useSession } from '@/context/SessionContext'
import { useToast } from '@/context/ToastContext'
import type { Device, DeviceControl } from '@/types/device'

const ACTION_LABELS: Record<string, string> = {
  turn_on: 'Bật',
  turn_off: 'Tắt',
  unlock: 'Mở khóa',
  lock: 'Khóa',
  start_recording: 'Bật ghi hình',
  stop_recording: 'Tắt ghi hình',
  set_brightness: 'Đặt độ sáng',
  set_temperature: 'Đặt nhiệt độ',
  set_volume: 'Đặt âm lượng',
  set_position: 'Đặt vị trí',
  set_speed: 'Đặt tốc độ',
  set_mode: 'Đặt chế độ',
  set_fan: 'Đặt quạt',
  set_preset: 'Đặt vị trí định sẵn',
  open: 'Mở',
  close: 'Đóng',
  disable: 'Vô hiệu hóa',
}

function actionsForControl(control: DeviceControl): string[] {
  if (control.type === 'toggle') {
    if (control.key === 'power') return ['turn_on', 'turn_off']
    if (control.key === 'recording') return ['start_recording', 'stop_recording']
    return [control.key]
  }
  if (control.type === 'action') {
    return ['lock', 'unlock', 'disable'].includes(control.key) ? [control.key] : []
  }
  if (control.type === 'enum' && control.key === 'preset') {
    return ['set_preset', 'open', 'close']
  }
  return [`set_${control.key}`]
}

function actionsForDevice(device: Device | undefined): string[] {
  return [...new Set((device?.controls ?? []).flatMap(actionsForControl))]
}

export function HitlSettingsPanel() {
  const { isAdmin } = useSession()
  const { devices } = useDevices()
  const { showToast } = useToast()
  const [policies, setPolicies] = useState<HitlPolicyWrite[]>([])
  const [timeout, setTimeoutValue] = useState(30)
  const [deviceId, setDeviceId] = useState('')
  const [action, setAction] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const selectedDevice = devices.find((device) => device.id === deviceId)
  const availableActions = useMemo(() => actionsForDevice(selectedDevice), [selectedDevice])

  useEffect(() => {
    let cancelled = false
    void Promise.all([fetchHomeSettings(), fetchHitlPolicies()])
      .then(([settings, rows]) => {
        if (cancelled) return
        setTimeoutValue(settings.hitl_timeout_seconds)
        setPolicies(rows.map(({ device_id, action, require_confirm }) => ({
          device_id,
          action,
          require_confirm,
        })))
      })
      .catch((error: unknown) => {
        if (!cancelled) showToast(error instanceof Error ? error.message : 'Không tải được cài đặt HITL', 'error')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [showToast])

  useEffect(() => {
    if (!deviceId && devices[0]) setDeviceId(devices[0].id)
  }, [deviceId, devices])

  useEffect(() => {
    if (!availableActions.includes(action)) setAction(availableActions[0] ?? '')
  }, [action, availableActions])

  const addPolicy = () => {
    if (!deviceId || !action) return
    if (policies.some((item) => item.device_id === deviceId && item.action === action)) {
      showToast('Policy này đã có trong danh sách', 'warning')
      return
    }
    setPolicies((current) => [...current, { device_id: deviceId, action, require_confirm: true }])
  }

  const save = async () => {
    setSaving(true)
    try {
      const [settings, rows] = await Promise.all([
        patchHomeSettings({ hitl_timeout_seconds: timeout }),
        replaceHitlPolicies(policies),
      ])
      setTimeoutValue(settings.hitl_timeout_seconds)
      setPolicies(rows.map(({ device_id, action: savedAction, require_confirm }) => ({
        device_id,
        action: savedAction,
        require_confirm,
      })))
      showToast('Đã lưu cài đặt HITL', 'success')
      window.dispatchEvent(new CustomEvent('hitl.settings.updated', {
        detail: { timeoutSeconds: settings.hitl_timeout_seconds },
      }))
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Không lưu được cài đặt HITL', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="rounded-2xl border border-[#E6ECE3] bg-white p-4 text-sm text-[#718076]">Đang tải cài đặt HITL…</div>

  return (
    <div className="space-y-3 pb-2">
      <section className="rounded-2xl border border-[#E6ECE3] bg-white p-4 shadow-sm">
        <h3 className="font-display text-sm font-bold text-[#1C2721]">Xác nhận hành động nhạy cảm</h3>
        <p className="mt-1 text-xs text-[#718076]">Agent phải nhận được xác nhận trước khi thực hiện các hành động bên dưới.</p>
        <label className="mt-4 flex items-center justify-between gap-4 text-xs font-semibold text-[#44534A]">
          Thời gian chờ xác nhận
          <span className="flex items-center gap-2">
            <input
              type="number"
              min={5}
              max={300}
              disabled={!isAdmin}
              value={timeout}
              onChange={(event) => setTimeoutValue(Math.max(5, Math.min(300, Number(event.target.value) || 5)))}
              className="w-20 rounded-lg border border-[#D8E1D8] px-2 py-1.5 text-right outline-none focus:border-[#2D6A4F] disabled:bg-[#F4F6F3]"
            />
            giây
          </span>
        </label>
      </section>

      <section className="rounded-2xl border border-[#E6ECE3] bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-sm font-bold text-[#1C2721]">Chính sách theo thiết bị</h3>
          <span className="text-xs text-[#718076]">{policies.length} policy</span>
        </div>
        <div className="mt-3 space-y-2">
          {policies.length === 0 ? <p className="rounded-xl bg-[#F8FAF7] p-3 text-xs text-[#718076]">Chưa có hành động nào bắt buộc xác nhận.</p> : null}
          {policies.map((policy, index) => {
            const device = devices.find((item) => item.id === policy.device_id)
            return (
              <div key={`${policy.device_id}:${policy.action}`} className="flex items-center gap-3 rounded-xl bg-[#F8FAF7] p-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-bold text-[#1C2721]">{device?.name ?? policy.device_id}</p>
                  <p className="text-[10px] text-[#718076]">{ACTION_LABELS[policy.action] ?? policy.action}</p>
                </div>
                <button
                  type="button"
                  disabled={!isAdmin}
                  onClick={() => setPolicies((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, require_confirm: !item.require_confirm } : item))}
                  className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${policy.require_confirm ? 'bg-[#E2EFE5] text-[#1E4D38]' : 'bg-gray-200 text-gray-500'} disabled:opacity-60`}
                >
                  {policy.require_confirm ? 'Bắt buộc' : 'Tắt'}
                </button>
                {isAdmin ? <button type="button" onClick={() => setPolicies((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="text-xs font-semibold text-red-600">Xóa</button> : null}
              </div>
            )
          })}
        </div>

        {isAdmin ? (
          <div className="mt-3 grid gap-2 rounded-xl border border-dashed border-[#BFD2C2] p-3 sm:grid-cols-[1fr_1fr_auto]">
            <select value={deviceId} onChange={(event) => setDeviceId(event.target.value)} className="rounded-lg border border-[#D8E1D8] bg-white px-2 py-2 text-xs outline-none">
              {devices.map((device) => <option key={device.id} value={device.id}>{device.name}</option>)}
            </select>
            <select value={action} onChange={(event) => setAction(event.target.value)} className="rounded-lg border border-[#D8E1D8] bg-white px-2 py-2 text-xs outline-none">
              {availableActions.map((item) => <option key={item} value={item}>{ACTION_LABELS[item] ?? item}</option>)}
            </select>
            <button type="button" disabled={!deviceId || !action} onClick={addPolicy} className="rounded-lg bg-[#E2EFE5] px-3 py-2 text-xs font-bold text-[#1E4D38] disabled:opacity-50">Thêm</button>
          </div>
        ) : null}

        {isAdmin ? <div className="mt-4 flex justify-end"><button type="button" disabled={saving} onClick={() => void save()} className="rounded-xl bg-[#1E4D38] px-4 py-2 text-xs font-bold text-white disabled:opacity-50">{saving ? 'Đang lưu…' : 'Lưu cài đặt'}</button></div> : <p className="mt-3 text-xs text-[#718076]">Chỉ quản trị viên có thể thay đổi chính sách HITL.</p>}
      </section>
    </div>
  )
}
