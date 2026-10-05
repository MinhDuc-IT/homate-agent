import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { CloseIcon } from '@/assets/icons/CommonIcons'
import {
  ClapperboardIcon,
  MoonIcon,
  SparklesIcon,
  SunIcon,
} from '@/assets/icons/HomemateIcons'
import { NavHomeIcon } from '@/assets/icons/HomemateIcons'
import {
  BulbIcon,
  CameraIcon,
  CurtainIcon,
  DropletIcon,
  FanIcon,
  FlameIcon,
  LockIcon,
  PlugIcon,
  PlusIcon,
  SnowflakeIcon,
  SpeakerIcon,
  TvIcon,
} from '@/assets/icons/HomeMindIcons'
import {
  createScene,
  deleteScene,
  fetchScenes,
  updateScene,
  type Scene,
} from '@/api/scenes'
import { TabletScreen } from '@/components/layout/TabletScreen'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import {
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
} from '@/components/ui/Modal'
import { useDevices } from '@/context/DevicesContext'
import { useSession } from '@/context/SessionContext'
import { useToast } from '@/context/ToastContext'
import { useNavigate } from 'react-router-dom'
import { ROUTES } from '@/config/routes'
import { useSchedules } from '@/hooks/useSchedules'
import type { Device, DeviceIconKind } from '@/types/device'
import {
  actionsForDevice,
  executeSceneSteps,
  formatSceneStepLabel,
  isDeviceKind,
} from '@/utils/sceneSteps'

type DraftStep = {
  key: string
  device_id: string
  action: string
  parameters: Record<string, unknown>
}

type SceneVisual = {
  img: string | null
  iconBg: string
  icon: typeof SunIcon
}

const SCENE_VISUALS: Record<string, SceneVisual> = {
  guests: {
    img: '/assets/images/scene_home.png',
    icon: NavHomeIcon,
    iconBg: 'bg-[#2D6A4F]',
  },
  sleep: {
    img: '/assets/images/scene_sleep.png',
    icon: MoonIcon,
    iconBg: 'bg-[#1E4D38]',
  },
  home: {
    img: '/assets/images/scene_home.png',
    icon: NavHomeIcon,
    iconBg: 'bg-[#2D6A4F]',
  },
}

function newKey() {
  return crypto.randomUUID()
}

function sceneToDraft(scene: Scene): DraftStep[] {
  return scene.steps.map((step) => ({
    key: step.id,
    device_id: step.device_id,
    action: step.action,
    parameters: { ...step.parameters },
  }))
}

function sceneVisual(scene: Scene): SceneVisual {
  const preset = SCENE_VISUALS[scene.id]
  if (preset) return preset

  const keyword = scene.voice_keyword.toLowerCase()
  if (keyword.includes('ngủ')) {
    return {
      img: '/assets/images/scene_sleep.png',
      icon: MoonIcon,
      iconBg: 'bg-[#1E4D38]',
    }
  }
  if (keyword.includes('sáng')) {
    return {
      img: '/assets/images/scene_morning.png',
      icon: SunIcon,
      iconBg: 'bg-amber-500',
    }
  }
  if (keyword.includes('phim')) {
    return {
      img: '/assets/images/scene_movie.png',
      icon: ClapperboardIcon,
      iconBg: 'bg-[#1E4D38]',
    }
  }
  if (keyword.includes('nhà') || keyword.includes('về')) {
    return {
      img: '/assets/images/scene_home.png',
      icon: NavHomeIcon,
      iconBg: 'bg-[#2D6A4F]',
    }
  }

  return {
    img: null,
    icon: SparklesIcon,
    iconBg: 'bg-[#2D6A4F]',
  }
}

function sceneDescription(scene: Scene): string {
  if (scene.steps.length === 0) return 'Chưa có hành động nào'
  const preview = scene.steps
    .slice(0, 2)
    .map((step) => formatSceneStepLabel(step.device_name, step.action, step.parameters))
    .join(' · ')
  if (scene.steps.length > 2) return `${preview} · +${scene.steps.length - 2}`
  return preview
}

function deviceIcon(kind: string, className = 'h-3.5 w-3.5'): ReactNode {
  const resolved: DeviceIconKind = isDeviceKind(kind) ? kind : 'plug'
  switch (resolved) {
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

function GreenToggle({
  on,
  onToggle,
}: {
  on: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors ${
        on ? 'bg-[#2D6A4F]' : 'bg-[#CBD5CE]'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition ${
          on ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </button>
  )
}

export function SceneScreen() {
  const navigate = useNavigate()
  const { data: schedules } = useSchedules()
  const { showToast } = useToast()
  const { isAdmin } = useSession()
  const { devices, applyAction } = useDevices()

  const [scenes, setScenes] = useState<Scene[]>([])
  const [loading, setLoading] = useState(true)
  const [runningSceneId, setRunningSceneId] = useState<string | null>(null)
  const [editingSceneId, setEditingSceneId] = useState<string | null>(null)
  const [showBanner, setShowBanner] = useState(true)

  const [editName, setEditName] = useState('')
  const [editEnabled, setEditEnabled] = useState(true)
  const [draftSteps, setDraftSteps] = useState<DraftStep[]>([])
  const [saving, setSaving] = useState(false)

  const [createOpen, setCreateOpen] = useState(false)
  const [newName, setNewName] = useState('')

  const deviceById = useMemo(
    () => Object.fromEntries(devices.map((device) => [device.id, device])),
    [devices],
  )

  const editingScene = scenes.find((scene) => scene.id === editingSceneId) ?? null
  const firstScene = scenes[0] ?? null

  const loadScenes = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchScenes()
      setScenes(data)
    } catch (err) {
      showToast(
        err instanceof Error ? err.message : 'Không tải được kịch bản',
        'error',
      )
    } finally {
      setLoading(false)
    }
  }, [showToast])

  useEffect(() => {
    void loadScenes()
  }, [loadScenes])

  const startEditing = (scene: Scene) => {
    if (!isAdmin) return
    setEditingSceneId(scene.id)
    setEditName(scene.name)
    setEditEnabled(scene.is_enabled)
    setDraftSteps(sceneToDraft(scene))
  }

  const handleActivate = async (scene: Scene) => {
    if (!scene.is_enabled) {
      showToast(`Kịch bản “${scene.name}” đang tắt`, 'info')
      return
    }
    if (scene.steps.length === 0) {
      showToast(`Kịch bản “${scene.name}” chưa có hành động`, 'info')
      return
    }

    setRunningSceneId(scene.id)
    showToast(`Đang kích hoạt “${scene.name}”…`, 'info')
    try {
      const { ok, fail } = await executeSceneSteps(
        scene.steps,
        devices,
        applyAction,
      )
      if (fail === 0) {
        showToast(`Đã kích hoạt “${scene.name}” (${ok} hành động)`, 'success')
      } else {
        showToast(
          `“${scene.name}”: ${ok} thành công, ${fail} thất bại`,
          fail === ok ? 'info' : 'error',
        )
      }
    } finally {
      setRunningSceneId(null)
    }
  }

  const addStep = () => {
    const device = devices[0]
    if (!device) {
      showToast('Chưa có thiết bị', 'error')
      return
    }
    const option = actionsForDevice(device)[0]
    setDraftSteps((prev) => [
      ...prev,
      {
        key: newKey(),
        device_id: device.id,
        action: option.action,
        parameters: { ...option.parameters },
      },
    ])
  }

  const changeStepDevice = (key: string, deviceId: string) => {
    const device = deviceById[deviceId]
    if (!device) return
    const option = actionsForDevice(device)[0]
    setDraftSteps((prev) =>
      prev.map((step) =>
        step.key === key
          ? {
              ...step,
              device_id: deviceId,
              action: option.action,
              parameters: { ...option.parameters },
            }
          : step,
      ),
    )
  }

  const changeStepAction = (key: string, action: string, device: Device) => {
    const option = actionsForDevice(device).find((item) => item.action === action)
    setDraftSteps((prev) =>
      prev.map((step) =>
        step.key === key
          ? {
              ...step,
              action,
              parameters: { ...(option?.parameters ?? {}) },
            }
          : step,
      ),
    )
  }

  const saveEditing = async () => {
    if (!editingScene) return
    const title = editName.trim()
    if (!title) {
      showToast('Nhập tên kịch bản', 'error')
      return
    }

    setSaving(true)
    try {
      const updated = await updateScene(editingScene.id, {
        name: title,
        voice_keyword: title,
        is_enabled: editEnabled,
        steps: draftSteps.map((step) => ({
          device_id: step.device_id,
          action: step.action,
          parameters: step.parameters,
        })),
      })
      setScenes((prev) => prev.map((scene) => (scene.id === updated.id ? updated : scene)))
      setDraftSteps(sceneToDraft(updated))
      showToast('Đã lưu kịch bản', 'success')
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Lưu thất bại', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!editingScene) return
    if (!window.confirm(`Xóa kịch bản “${editingScene.name}”?`)) return

    setSaving(true)
    try {
      await deleteScene(editingScene.id)
      setEditingSceneId(null)
      await loadScenes()
      showToast('Đã xóa kịch bản', 'success')
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Xóa thất bại', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleCreate = async () => {
    const title = newName.trim()
    if (!title) {
      showToast('Nhập tên kịch bản', 'error')
      return
    }

    setSaving(true)
    try {
      const created = await createScene({
        name: title,
        voice_keyword: title,
        steps: [],
      })
      setCreateOpen(false)
      setNewName('')
      await loadScenes()
      startEditing(created)
      showToast('Đã tạo kịch bản', 'success')
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Tạo thất bại', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <TabletScreen>
      <div className="flex h-full min-h-0 flex-col gap-2">
        <div className="shrink-0">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h2 className="font-display text-xs font-bold text-[#1C2721]">
                Kịch bản
              </h2>
              <p className="text-[10px] text-[#718076]">
                Một chạm để thay đổi không gian phù hợp mọi khoảnh khắc.
              </p>
            </div>
            {isAdmin ? (
              <button
                type="button"
                onClick={() => setCreateOpen(true)}
                className="flex items-center gap-1 rounded-full bg-[#1E4D38] px-2.5 py-1 text-[9px] font-bold text-white shadow-sm hover:bg-[#153828]"
              >
                <PlusIcon className="h-3 w-3" />
                Tạo kịch bản
              </button>
            ) : null}
          </div>

          {loading && scenes.length === 0 ? (
            <div className="flex justify-center py-6">
              <LoadingSpinner />
            </div>
          ) : scenes.length === 0 ? (
            <p className="py-4 text-center text-[10px] text-[#88968E]">
              Chưa có kịch bản nào.
            </p>
          ) : (
            <div className="mt-2 grid grid-cols-2 gap-2 lg:grid-cols-4">
              {scenes.map((scene) => {
                const visual = sceneVisual(scene)
                const Icon = visual.icon
                const isRunning = runningSceneId === scene.id
                const isEditing = editingSceneId === scene.id
                return (
                  <div
                    key={scene.id}
                    className={`flex flex-col justify-between overflow-hidden rounded-2xl border bg-white shadow-sm ${
                      isEditing
                        ? 'border-2 border-[#1E4D38]'
                        : 'border-[#E6ECE3]'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => (isAdmin ? startEditing(scene) : undefined)}
                      className={`text-left ${isAdmin ? 'cursor-pointer' : 'cursor-default'}`}
                    >
                      <div className="relative h-20 w-full overflow-hidden bg-[#F4FAF5]">
                        {visual.img ? (
                          <img
                            src={visual.img}
                            alt={scene.name}
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          <div className="flex h-full items-center justify-center text-[#2D6A4F]">
                            <Icon className="h-8 w-8" />
                          </div>
                        )}
                        <div
                          className={`absolute bottom-2 left-2 flex h-6 w-6 items-center justify-center rounded-full text-white shadow-md ${visual.iconBg}`}
                        >
                          <Icon className="h-3.5 w-3.5" />
                        </div>
                        {!scene.is_enabled ? (
                          <span className="absolute top-2 right-2 rounded-md bg-black/50 px-1.5 py-px text-[8px] font-bold text-white">
                            Tắt
                          </span>
                        ) : null}
                      </div>
                      <div className="p-2">
                        <h3 className="font-display text-[11px] font-bold text-[#1C2721]">
                          {scene.name}
                        </h3>
                        <p className="mt-0.5 line-clamp-2 text-[9px] leading-snug text-[#718076]">
                          {sceneDescription(scene)}
                        </p>
                      </div>
                    </button>
                    <div className="p-2 pt-0">
                      <button
                        type="button"
                        onClick={() => void handleActivate(scene)}
                        disabled={isRunning}
                        className="flex w-full items-center justify-center gap-1 rounded-full border border-[#D5E5D8] bg-[#F4FAF5] py-1 text-[9px] font-bold text-[#1E4D38] hover:bg-[#E2EFE5] disabled:opacity-60"
                      >
                        <span>▶</span>
                        <span>{isRunning ? 'Đang chạy…' : 'Kích hoạt'}</span>
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-1 gap-2 lg:grid-cols-12">
          <div className="flex min-h-0 flex-col gap-2 overflow-y-auto lg:col-span-8">
            {editingScene && isAdmin ? (
              <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
                <div className="flex shrink-0 items-center justify-between gap-2">
                  <div>
                    <h2 className="font-display text-xs font-bold text-[#1C2721]">
                      Chỉnh sửa kịch bản
                    </h2>
                    <p className="text-[10px] text-[#718076]">
                      {editingScene.steps.length} hành động hiện tại
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setEditingSceneId(null)}
                    className="text-[#A8B5AD] hover:text-[#1E4D38]"
                    aria-label="Đóng"
                  >
                    <CloseIcon className="h-4 w-4" />
                  </button>
                </div>

                <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto]">
                  <input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    placeholder="Tên kịch bản"
                    className="rounded-lg border border-[#E0E7DE] bg-[#F8FAF7] px-2.5 py-1.5 text-[10px] font-semibold text-[#1C2721] outline-none focus:border-[#2D6A4F]"
                  />
                  <label className="flex items-center gap-2 text-[10px] font-semibold text-[#5A6860]">
                    <GreenToggle
                      on={editEnabled}
                      onToggle={() => setEditEnabled((value) => !value)}
                    />
                    Bật kịch bản
                  </label>
                </div>

                <div className="mt-2 min-h-0 flex-1 space-y-1.5 overflow-y-auto">
                  {draftSteps.map((step, index) => {
                    const device = deviceById[step.device_id]
                    const options = device ? actionsForDevice(device) : []
                    const kind = device?.kind ?? step.device_id
                    const label = formatSceneStepLabel(
                      device?.name ?? step.device_id,
                      step.action,
                      step.parameters,
                    )
                    return (
                      <div
                        key={step.key}
                        className="rounded-xl border border-[#E6ECE3] bg-[#F8FAF7] p-2"
                      >
                        <div className="mb-1.5 flex items-center gap-2">
                          <span className="text-[9px] font-bold text-[#88968E]">
                            {index + 1}
                          </span>
                          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-[#E2EFE5] text-[#1E4D38]">
                            {deviceIcon(kind)}
                          </span>
                          <p className="min-w-0 flex-1 truncate text-[9px] text-[#718076]">
                            {label}
                          </p>
                          <button
                            type="button"
                            onClick={() =>
                              setDraftSteps((prev) =>
                                prev.filter((item) => item.key !== step.key),
                              )
                            }
                            className="text-[#A8B5AD] hover:text-[#1E4D38]"
                            aria-label="Xóa hành động"
                          >
                            <CloseIcon className="h-3.5 w-3.5" />
                          </button>
                        </div>
                        <div className="grid gap-1.5 sm:grid-cols-2">
                          <select
                            value={step.device_id}
                            onChange={(e) =>
                              changeStepDevice(step.key, e.target.value)
                            }
                            className="rounded-md border border-[#E0E7DE] bg-white px-2 py-1 text-[9px] font-medium text-[#1C2721] outline-none"
                          >
                            {devices.map((item) => (
                              <option key={item.id} value={item.id}>
                                {item.name}
                              </option>
                            ))}
                          </select>
                          <select
                            value={step.action}
                            onChange={(e) =>
                              device &&
                              changeStepAction(step.key, e.target.value, device)
                            }
                            className="rounded-md border border-[#E0E7DE] bg-white px-2 py-1 text-[9px] font-medium text-[#1C2721] outline-none"
                          >
                            {options.map((option) => (
                              <option key={option.action} value={option.action}>
                                {option.label}
                              </option>
                            ))}
                            {options.every((option) => option.action !== step.action) ? (
                              <option value={step.action}>{step.action}</option>
                            ) : null}
                          </select>
                        </div>
                        {step.action === 'set_brightness' ? (
                          <input
                            type="number"
                            min={1}
                            max={100}
                            value={Number(step.parameters.brightness ?? 60)}
                            onChange={(e) =>
                              setDraftSteps((prev) =>
                                prev.map((item) =>
                                  item.key === step.key
                                    ? {
                                        ...item,
                                        parameters: {
                                          brightness: Number(e.target.value),
                                        },
                                      }
                                    : item,
                                ),
                              )
                            }
                            className="mt-1.5 w-full rounded-md border border-[#E0E7DE] bg-white px-2 py-1 text-[9px] outline-none"
                            aria-label="Độ sáng"
                          />
                        ) : null}
                        {step.action === 'set_temperature' ? (
                          <input
                            type="number"
                            min={16}
                            max={30}
                            value={Number(step.parameters.temperature ?? 26)}
                            onChange={(e) =>
                              setDraftSteps((prev) =>
                                prev.map((item) =>
                                  item.key === step.key
                                    ? {
                                        ...item,
                                        parameters: {
                                          temperature: Number(e.target.value),
                                        },
                                      }
                                    : item,
                                ),
                              )
                            }
                            className="mt-1.5 w-full rounded-md border border-[#E0E7DE] bg-white px-2 py-1 text-[9px] outline-none"
                            aria-label="Nhiệt độ"
                          />
                        ) : null}
                      </div>
                    )
                  })}
                </div>

                <div className="mt-2 flex shrink-0 flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    onClick={addStep}
                    className="rounded-full border border-dashed border-[#2D6A4F] px-2.5 py-1 text-[9px] font-bold text-[#1E4D38] hover:bg-[#EAF5ED]"
                  >
                    + Thêm hành động
                  </button>
                  <div className="ml-auto flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => void handleDelete()}
                      disabled={saving}
                      className="rounded-full border border-[#E0E7DE] px-2.5 py-1 text-[9px] font-bold text-[#88968E] hover:bg-[#F8FAF7]"
                    >
                      Xóa
                    </button>
                    <button
                      type="button"
                      onClick={() => void saveEditing()}
                      disabled={saving}
                      className="rounded-full bg-[#1E4D38] px-3 py-1 text-[9px] font-bold text-white hover:bg-[#153828] disabled:opacity-60"
                    >
                      {saving ? 'Đang lưu…' : 'Lưu'}
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
                {firstScene ? (
                  <>
                    <div className="flex shrink-0 items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="font-display text-xs font-bold text-[#1C2721]">{firstScene.name}</h2>
                          <span className={`rounded-md px-1.5 py-px text-[8px] font-bold ${firstScene.is_enabled ? 'bg-[#E8F5EB] text-[#2E7D32]' : 'bg-[#F1F3F1] text-[#718076]'}`}>
                            {firstScene.is_enabled ? 'Đang bật' : 'Đã tắt'}
                          </span>
                        </div>
                        <p className="mt-0.5 text-[10px] text-[#718076]">Chi tiết kịch bản đầu tiên · {firstScene.steps.length} hành động</p>
                      </div>
                      {isAdmin ? <button type="button" onClick={() => startEditing(firstScene)} className="rounded-full border border-[#D5E5D8] px-2.5 py-1 text-[9px] font-bold text-[#1E4D38] hover:bg-[#EAF5ED]">Chỉnh sửa</button> : null}
                    </div>
                    <div className="mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto">
                      {firstScene.steps.length === 0 ? <p className="rounded-xl bg-[#F8FAF7] p-4 text-center text-[10px] text-[#718076]">Kịch bản này chưa có hành động.</p> : firstScene.steps.map((step, index) => (
                        <div key={step.id || `${step.device_id}-${index}`} className="flex items-center gap-2 rounded-xl bg-[#F8FAF7] p-2.5">
                          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#1E4D38] text-[9px] font-bold text-white">{index + 1}</span>
                          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#E2EFE5] text-[#1E4D38]">{deviceIcon(deviceById[step.device_id]?.kind ?? step.device_kind)}</span>
                          <div className="min-w-0 flex-1"><p className="truncate text-[10px] font-bold text-[#1C2721]">{step.device_name || deviceById[step.device_id]?.name || step.device_id}</p><p className="truncate text-[9px] text-[#718076]">{formatSceneStepLabel(step.device_name || deviceById[step.device_id]?.name || step.device_id, step.action, step.parameters)}</p></div>
                        </div>
                      ))}
                    </div>
                    <button type="button" onClick={() => void handleActivate(firstScene)} disabled={runningSceneId === firstScene.id || !firstScene.is_enabled} className="mt-2 shrink-0 rounded-full bg-[#1E4D38] py-1.5 text-[9px] font-bold text-white disabled:opacity-50">{runningSceneId === firstScene.id ? 'Đang chạy…' : 'Kích hoạt kịch bản'}</button>
                  </>
                ) : <div className="flex flex-1 items-center justify-center text-center text-[10px] text-[#718076]">Chưa có kịch bản để hiển thị.</div>}
              </div>
            )}
          </div>

          <div className="flex min-h-0 flex-col rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm lg:col-span-4">
            <h3 className="shrink-0 font-display text-xs font-bold text-[#1C2721]">
              Lịch sắp tới
            </h3>
            <div className="mt-2 min-h-0 flex-1 space-y-1.5 overflow-y-auto text-[10px]">
              {schedules.slice(0, 4).map((item) => {
                const Icon = item.target_type === 'scene' ? SparklesIcon : SunIcon
                return (
                  <div
                    key={item.id}
                    className="flex items-center gap-2 rounded-xl bg-[#F8FAF7] p-2"
                  >
                    <span
                      className="flex h-6 w-6 items-center justify-center rounded-lg bg-[#E2EFE5] text-[#1E4D38]"
                    >
                      <Icon className="h-3.5 w-3.5" />
                    </span>
                    <div>
                      <p className="font-bold text-[#1C2721]">
                      {item.next_run_at ? new Date(item.next_run_at).toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' }) : '—'}{' '}
                        <span className="font-normal text-[#718076]">
                          {item.name}
                        </span>
                      </p>
                      <p className="text-[9px] text-[#88968E]">{item.schedule_type === 'once' ? 'Một lần' : 'Lặp lại'}</p>
                    </div>
                  </div>
                )
              })}
              {schedules.length === 0 && <p className="py-4 text-center text-[#88968E]">Chưa có lịch sắp tới.</p>}
            </div>
            <button
              type="button"
              onClick={() => navigate(ROUTES.schedules)}
              className="mt-1.5 flex shrink-0 items-center justify-between rounded-lg px-1.5 py-1 text-[10px] font-semibold text-[#1E4D38] hover:bg-[#E2EFE5]"
            >
              <span>Xem lịch đầy đủ</span>
              <span>›</span>
            </button>
          </div>
        </div>

        {showBanner ? (
          <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 rounded-2xl border border-[#D5E5D8] bg-[#EAF5ED] p-2.5 text-[10px]">
            <div className="flex items-center gap-2 text-[#1C2721]">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white text-[#2D6A4F] shadow-xs">
                <SparklesIcon className="h-3.5 w-3.5" />
              </span>
              <div>
                <p className="font-bold text-[#1E4D38]">Gợi ý cho bạn</p>
                <p className="text-[#3B4D42]">
                  Kích hoạt “Về nhà” khi bạn trong bán kính 500m.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => showToast('Đã thiết lập bán kính 500m', 'success')}
                className="rounded-full bg-white px-3 py-1 text-[9px] font-bold text-[#1E4D38] shadow-xs"
              >
                Thiết lập
              </button>
              <button
                type="button"
                onClick={() => setShowBanner(false)}
                className="text-[#A8B5AD] hover:text-[#1E4D38]"
                aria-label="Close"
              >
                ✕
              </button>
            </div>
          </div>
        ) : null}
      </div>

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm">
        <ModalHeader
          onClose={() => setCreateOpen(false)}
          title="Tạo kịch bản"
        />
        <ModalBody>
          <label className="flex flex-col gap-1 text-[10px] font-semibold text-[#5A6860]">
            Tên kịch bản
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Đón khách"
              className="rounded-lg border border-[#E0E7DE] bg-[#F8FAF7] px-2.5 py-1.5 text-[11px] font-medium text-[#1C2721] outline-none focus:border-[#2D6A4F]"
            />
          </label>
          <p className="mt-1 text-[9px] text-[#88968E]">
            Nói tên này để kích hoạt kịch bản bằng giọng nói.
          </p>
        </ModalBody>
        <ModalFooter>
          <button
            type="button"
            onClick={() => setCreateOpen(false)}
            className="rounded-lg border border-[#E0E7DE] px-3 py-1.5 text-[10px] font-semibold text-[#5A6860]"
          >
            Hủy
          </button>
          <button
            type="button"
            onClick={() => void handleCreate()}
            disabled={saving}
            className="rounded-lg bg-[#1E4D38] px-3 py-1.5 text-[10px] font-semibold text-white hover:bg-[#153828] disabled:opacity-60"
          >
            Tạo
          </button>
        </ModalFooter>
      </Modal>
    </TabletScreen>
  )
}
