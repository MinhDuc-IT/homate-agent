import { useEffect, useMemo, useState } from 'react'
import { CloseIcon } from '@/assets/icons/CommonIcons'
import { PlusIcon } from '@/assets/icons/HomeMindIcons'
import { fetchDevices } from '@/api/devices'
import {
  fetchCommandLogs,
  fetchHitlPolicies,
  fetchHomeSettings,
  patchHomeSettings,
  replaceHitlPolicies,
  type CommandLog,
  type HitlPolicy,
  type HitlPolicyWrite,
  type HomeSettings,
} from '@/api/settings'
import { ToggleSwitch } from '@/components/homemind/ToggleSwitch'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Modal, ModalBody, ModalFooter, ModalHeader } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import { useToast } from '@/context/ToastContext'
import type { Device } from '@/types/device'
import { actionsForDevice } from '@/utils/sceneSteps'
import { cn } from '@/utils/cn'

const toneClass = {
  success: 'text-success',
  warning: 'text-warning',
  muted: 'text-text-muted',
  secondary: 'text-text-secondary',
  error: 'text-danger',
} as const

type Tone = keyof typeof toneClass

type DraftRow = {
  key: string
  device_id: string
  action: string
}

function resultTone(result: string): Tone {
  if (result.includes('Hoàn thành')) return 'success'
  if (result.includes('Chờ') || result.includes('HITL')) return 'warning'
  if (result.includes('hỏi')) return 'secondary'
  if (result.includes('Không')) return 'error'
  return 'muted'
}

function formatTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
}

function newRowKey(): string {
  return `row-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function defaultActionFor(device: Device | undefined): string {
  if (!device) return ''
  return actionsForDevice(device)[0]?.action ?? ''
}

function policySummaryLabel(
  policy: HitlPolicy,
  deviceById: Record<string, Device>,
): string {
  const device = deviceById[policy.device_id]
  const name = device?.name || policy.device_name || policy.device_id
  const actionLabel =
    device
      ? actionsForDevice(device).find((o) => o.action === policy.action)?.label
      : undefined
  return `${name} → ${actionLabel || policy.action}`
}

export function PrivacyLog() {
  const { showToast } = useToast()
  const [settings, setSettings] = useState<HomeSettings | null>(null)
  const [logs, setLogs] = useState<CommandLog[]>([])
  const [policies, setPolicies] = useState<HitlPolicy[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [loading, setLoading] = useState(true)
  const [savingToggle, setSavingToggle] = useState(false)
  const [hitlOpen, setHitlOpen] = useState(false)
  const [draftRows, setDraftRows] = useState<DraftRow[]>([])
  const [savingHitl, setSavingHitl] = useState(false)

  const deviceById = useMemo(
    () => Object.fromEntries(devices.map((d) => [d.id, d])),
    [devices],
  )

  async function loadAll() {
    setLoading(true)
    try {
      const [nextSettings, nextLogs, nextPolicies, nextDevices] = await Promise.all([
        fetchHomeSettings(),
        fetchCommandLogs(50),
        fetchHitlPolicies(),
        fetchDevices(),
      ])
      setSettings(nextSettings)
      setLogs(nextLogs)
      setPolicies(nextPolicies)
      setDevices(nextDevices)
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Không tải được cài đặt', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount once
  }, [])

  async function onToggleLog(next: boolean) {
    if (!settings || savingToggle) return
    setSavingToggle(true)
    const previous = settings.command_log_enabled
    setSettings({ ...settings, command_log_enabled: next })
    try {
      const updated = await patchHomeSettings({ command_log_enabled: next })
      setSettings(updated)
      showToast(next ? 'Đã bật lưu nhật ký lệnh' : 'Đã tắt lưu nhật ký lệnh', 'success')
    } catch (err) {
      setSettings({ ...settings, command_log_enabled: previous })
      showToast(err instanceof Error ? err.message : 'Không lưu được cài đặt', 'error')
    } finally {
      setSavingToggle(false)
    }
  }

  function openHitlModal() {
    const rows: DraftRow[] = policies
      .filter((p) => p.require_confirm)
      .map((p) => ({
        key: newRowKey(),
        device_id: p.device_id,
        action: p.action,
      }))
    setDraftRows(rows)
    setHitlOpen(true)
  }

  function addRow() {
    const device = devices[0]
    if (!device) {
      showToast('Chưa có thiết bị để thêm policy', 'warning')
      return
    }
    setDraftRows((prev) => [
      ...prev,
      {
        key: newRowKey(),
        device_id: device.id,
        action: defaultActionFor(device),
      },
    ])
  }

  function updateRow(key: string, patch: Partial<DraftRow>) {
    setDraftRows((prev) =>
      prev.map((row) => {
        if (row.key !== key) return row
        const next = { ...row, ...patch }
        if (patch.device_id && patch.device_id !== row.device_id) {
          next.action = defaultActionFor(deviceById[patch.device_id])
        }
        return next
      }),
    )
  }

  function removeRow(key: string) {
    setDraftRows((prev) => prev.filter((row) => row.key !== key))
  }

  async function saveHitlPolicies() {
    const seen = new Set<string>()
    const body: HitlPolicyWrite[] = []
    for (const row of draftRows) {
      if (!row.device_id || !row.action) {
        showToast('Mỗi dòng cần chọn thiết bị và hành động', 'error')
        return
      }
      const id = `${row.device_id}::${row.action}`
      if (seen.has(id)) {
        showToast('Trùng policy — mỗi cặp thiết bị/hành động chỉ một dòng', 'error')
        return
      }
      seen.add(id)
      body.push({
        device_id: row.device_id,
        action: row.action,
        require_confirm: true,
      })
    }

    setSavingHitl(true)
    try {
      const updated = await replaceHitlPolicies(body)
      setPolicies(updated)
      setHitlOpen(false)
      showToast('Đã cập nhật chính sách HITL', 'success')
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Không lưu được HITL', 'error')
    } finally {
      setSavingHitl(false)
    }
  }

  const enabledPolicies = policies.filter((p) => p.require_confirm)

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <p className="mb-3 font-display text-[15px] font-bold text-text-primary">
          Riêng tư & bảo mật
        </p>
        <div className="flex items-center justify-between gap-3 border-b border-sidebar-border py-2.5">
          <div>
            <p className="text-sm text-text-primary">Lưu nhật ký lệnh</p>
            <p className="mt-0.5 text-xs text-text-secondary">
              Giữ trong {settings?.command_log_retention_days ?? 30} ngày, chỉ trên hub
            </p>
          </div>
          <button
            type="button"
            disabled={!settings || savingToggle || loading}
            onClick={() => void onToggleLog(!(settings?.command_log_enabled ?? true))}
            className="disabled:opacity-50"
          >
            <ToggleSwitch
              checked={settings?.command_log_enabled ?? true}
              aria-label="Lưu nhật ký lệnh"
            />
          </button>
        </div>
        <div className="flex items-center justify-between gap-3 py-2.5">
          <div className="min-w-0">
            <p className="text-sm text-text-primary">Hành động cần xác nhận HITL</p>
            <p className="mt-0.5 truncate text-xs text-text-secondary">
              {enabledPolicies.length
                ? enabledPolicies.map((p) => policySummaryLabel(p, deviceById)).join(', ')
                : 'Chưa có hành động nào'}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            disabled={loading}
            onClick={openHitlModal}
          >
            Tùy chỉnh
          </Button>
        </div>
      </Card>

      <Card>
        <p className="mb-3 font-display text-[15px] font-bold text-text-primary">
          Nhật ký lệnh gần đây
        </p>
        {loading ? (
          <p className="text-xs text-text-muted">Đang tải…</p>
        ) : logs.length === 0 ? (
          <p className="text-xs text-text-muted">Chưa có lệnh nào được ghi lại.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full table-fixed text-xs">
              <thead>
                <tr className="text-left text-text-secondary">
                  <th className="w-[28%] px-1 py-1.5 font-normal">Lệnh</th>
                  <th className="w-[20%] px-1 py-1.5 font-normal">Thời gian</th>
                  <th className="w-[26%] px-1 py-1.5 font-normal">Kết quả</th>
                  <th className="w-[26%] px-1 py-1.5 font-normal">Ghi chú</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((row) => (
                  <tr key={row.id} className="border-t border-sidebar-border">
                    <td className="truncate px-1 py-2 text-text-primary" title={row.utterance}>
                      {row.utterance}
                    </td>
                    <td className="px-1 py-2 text-text-secondary">{formatTime(row.created_at)}</td>
                    <td className={cn('px-1 py-2', toneClass[resultTone(row.result)])}>
                      {row.result}
                    </td>
                    <td
                      className={cn(
                        'truncate px-1 py-2',
                        row.note.includes('HITL') ? toneClass.warning : toneClass.muted,
                      )}
                      title={row.note}
                    >
                      {row.note || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal open={hitlOpen} onClose={() => setHitlOpen(false)} maxWidth="lg">
        <ModalHeader title="Chính sách xác nhận HITL" onClose={() => setHitlOpen(false)} />
        <ModalBody>
          <p className="mb-3 text-xs text-text-secondary">
            Thêm cặp thiết bị + hành động (cùng schema agent dùng khi chạy lệnh). Lưu sẽ
            thay thế toàn bộ danh sách hiện tại.
          </p>

          {draftRows.length === 0 ? (
            <p className="mb-3 rounded-lg border border-dashed border-sidebar-border px-3 py-6 text-center text-sm text-text-muted">
              Chưa có policy. Bấm «Thêm» để chọn thiết bị và hành động.
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {draftRows.map((row) => {
                const device = deviceById[row.device_id]
                const options = device ? actionsForDevice(device) : []
                return (
                  <div
                    key={row.key}
                    className="flex flex-wrap items-center gap-2 rounded-lg border border-sidebar-border px-3 py-2.5"
                  >
                    <Select
                      className="min-w-[160px] flex-1"
                      value={row.device_id}
                      onChange={(event) =>
                        updateRow(row.key, { device_id: event.target.value })
                      }
                      aria-label="Thiết bị"
                    >
                      {devices.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                      {!device && row.device_id ? (
                        <option value={row.device_id}>{row.device_id}</option>
                      ) : null}
                    </Select>
                    <Select
                      className="min-w-[140px] flex-1"
                      value={row.action}
                      onChange={(event) =>
                        updateRow(row.key, { action: event.target.value })
                      }
                      aria-label="Hành động"
                    >
                      {options.map((opt) => (
                        <option key={opt.action} value={opt.action}>
                          {opt.label}
                        </option>
                      ))}
                      {options.every((o) => o.action !== row.action) && row.action ? (
                        <option value={row.action}>{row.action}</option>
                      ) : null}
                    </Select>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-9 w-9 shrink-0"
                      aria-label="Xóa policy"
                      onClick={() => removeRow(row.key)}
                    >
                      <CloseIcon className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                )
              })}
            </div>
          )}

          <div className="mt-3">
            <Button
              variant="outline"
              size="sm"
              leftIcon={<PlusIcon className="h-3.5 w-3.5" />}
              onClick={addRow}
              disabled={devices.length === 0}
            >
              Thêm
            </Button>
          </div>
        </ModalBody>
        <ModalFooter>
          <Button variant="outline" onClick={() => setHitlOpen(false)} disabled={savingHitl}>
            Hủy
          </Button>
          <Button onClick={() => void saveHitlPolicies()} disabled={savingHitl}>
            {savingHitl ? 'Đang lưu…' : 'Lưu'}
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  )
}
