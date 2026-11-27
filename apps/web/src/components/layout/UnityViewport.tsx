import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { cn } from '@/utils/cn'
import { useDevices } from '@/context/DevicesContext'
import { SimulationDevicePanel } from '@/components/homemind/SimulationDevicePanel'

type ViewOption = { id: string; label: string }

export function UnityViewport({ className }: { className?: string }) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const { devices } = useDevices()
  const [deviceSync, setDeviceSync] = useState(false)
  const [status, setStatus] = useState<'loading' | 'ready' | 'unavailable'>('loading')
  const [attempt, setAttempt] = useState(0)
  const [views, setViews] = useState<ViewOption[]>([])
  const [focusDevices, setFocusDevices] = useState<ViewOption[]>([])
  const [focusedDevice, setFocusedDevice] = useState('')
  const [selectedDeviceId, setSelectedDeviceId] = useState('')
  const selectedDevice = devices.find(device => device.id === selectedDeviceId)
  function selectDevice(id: string) {
    setSelectedDeviceId(id)
    if (!id) setFocusedDevice('')
    iframeRef.current?.contentWindow?.postMessage({ type: 'homate:select-device', deviceId: id }, window.location.origin)
    iframeRef.current?.contentWindow?.focus()
  }
  const [hasAudio, setHasAudio] = useState(false)
  const [audioEnabled, setAudioEnabled] = useState(false)
  const [audioMessage, setAudioMessage] = useState('')
  const [runtimeReady, setRuntimeReady] = useState(false)
  const [runtimeGeneration, setRuntimeGeneration] = useState(0)
  const [selectedView, setSelectedView] = useState('overview')
  useEffect(() => {
    if (!runtimeReady || !deviceSync) return
    // Full snapshots restore the latest state after load and WebSocket reconnect.
    iframeRef.current?.contentWindow?.postMessage({
      type: 'homate:device-snapshot',
      devices: devices.filter(device => ['bulb', 'curtain', 'camera', 'tv', 'speaker', 'fan'].includes(device.kind)).map(device => ({
        id: device.id,
        power: device.state.power === true,
        brightness: typeof device.state.brightness === 'number' ? device.state.brightness : 100,
        position: typeof device.state.position === 'number' ? device.state.position : 0,
        recording: device.state.recording === true,
        volume: typeof device.state.volume === 'number' ? device.state.volume : 0,
        speed: typeof device.state.speed === 'number' ? device.state.speed : 0,
      })),
    }, window.location.origin)
  }, [devices, runtimeReady, deviceSync, runtimeGeneration])
  useLayoutEffect(() => {
    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin || event.source !== iframeRef.current?.contentWindow) return
      if (event.data?.type === 'homate:ready') {
        setRuntimeReady(true)
        setRuntimeGeneration(value => value + 1)
        setAudioEnabled(false)
        setSelectedDeviceId('')
      }
      if (event.data?.type === 'homate:audio-state') {
        setAudioEnabled(event.data.enabled === true)
        setAudioMessage(event.data.failed ? 'Không tải được nhạc. Bạn thử bật lại nhé.' : event.data.blocked ? 'Bấm Bật âm thanh để cho phép phát nhạc.' : '')
      }
      if (event.data?.type === 'homate:device-focused' && focusDevices.some(device => device.id === event.data.deviceId)) {
        setFocusedDevice(event.data.deviceId)
        setSelectedView('')
        selectDevice(event.data.deviceId)
      }
      if (event.data?.type === 'homate:device-selected' && (event.data.deviceId === '' || focusDevices.some(device => device.id === event.data.deviceId))) {
        setSelectedDeviceId(event.data.deviceId)
      }
      if (event.data?.type === 'homate:view-changed' && views.some(view => view.id === event.data.viewId)) {
        setSelectedView(event.data.viewId)
        setFocusedDevice('')
        selectDevice('')
      }
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [views, focusDevices])
  useEffect(() => {
    const controller = new AbortController()
    fetch('/unity/build-status.json', { cache: 'no-store', signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error('Unavailable')
        const info = await response.json()
        if (!controller.signal.aborted) {
          setViews(Array.isArray(info.views) ? info.views.filter((view: ViewOption) =>
            typeof view?.id === 'string' && /^[a-z-]{1,40}$/.test(view.id)
            && typeof view.label === 'string' && view.label.length <= 64) : [])
          setRuntimeReady(false)
          setDeviceSync(info.deviceSync === true)
          setFocusDevices(Array.isArray(info.focusDevices) ? info.focusDevices.filter((device: ViewOption) =>
            typeof device?.id === 'string' && /^[a-z0-9-]{1,100}$/.test(device.id)
            && typeof device.label === 'string' && device.label.length <= 100) : [])
          setHasAudio(Array.isArray(info.speakerAudio) && info.speakerAudio.length > 0)
          setAudioEnabled(false)
          setSelectedView('overview')
          setStatus(info.ready === true ? 'ready' : 'unavailable')
        }
      })
      .catch(() => { if (!controller.signal.aborted) setStatus('unavailable') })
    return () => controller.abort()
  }, [attempt])
  return (
    <section className={cn('relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl bg-[#101E19]', className)} aria-label="Mô hình nhà 3D">
      {status === 'ready' ? (
        <>
          {(views.length > 0 || focusDevices.length > 0) && <nav aria-label="Góc nhìn ngôi nhà" className="flex shrink-0 items-center gap-2 overflow-x-auto border-b border-[#DCE6DF] bg-white p-3">
            {views.map(view => <button key={view.id} type="button" disabled={!runtimeReady}
              aria-pressed={selectedView === view.id}
              onClick={() => {
                iframeRef.current?.contentWindow?.postMessage({ type: 'homate:set-view', viewId: view.id }, window.location.origin)
                iframeRef.current?.contentWindow?.focus()
              }}
              className={cn('shrink-0 rounded-lg px-3 py-2 text-sm font-medium transition-colors disabled:cursor-wait disabled:opacity-50',
                selectedView === view.id ? 'bg-[#1E4D38] text-white' : 'bg-[#EFF5F0] text-[#1E4D38] hover:bg-[#DDEBDF]')}>
              {view.label}
            </button>)}
            {focusDevices.length > 0 && <select aria-label="Xem thiết bị" value={focusedDevice} disabled={!runtimeReady}
              onChange={event => { if (event.target.value) {
                iframeRef.current?.contentWindow?.postMessage({ type: 'homate:focus-device', deviceId: event.target.value }, window.location.origin)
                iframeRef.current?.contentWindow?.focus()
              } }}
              className="max-w-56 shrink-0 rounded-lg border border-[#DCE6DF] bg-white px-3 py-2 text-sm text-[#1E4D38] disabled:opacity-50">
              <option value="">Xem thiết bị…</option>
              {focusDevices.map(device => <option key={device.id} value={device.id}>{devices.find(item => item.id === device.id)?.name ?? device.label}</option>)}
            </select>}
            {hasAudio && <button type="button" disabled={!runtimeReady} aria-pressed={audioEnabled}
              onClick={() => {
                const frame = iframeRef.current?.contentWindow as (Window & { homateSetAudioEnabled?: (enabled: boolean) => void }) | null
                frame?.homateSetAudioEnabled?.(!audioEnabled)
              }}
              className="shrink-0 rounded-lg bg-[#EFF5F0] px-3 py-2 text-sm text-[#1E4D38] disabled:opacity-50">
              {audioEnabled ? 'Tắt âm thanh' : 'Bật âm thanh'}
            </button>}
            {audioMessage && <span role="status" className="text-xs text-[#66746A]">{audioMessage}</span>}
            {!runtimeReady && <span role="status" className="shrink-0 text-xs text-[#66746A]">Đang tải mô hình…</span>}
          </nav>}
          <div className="border-b border-white/10 px-3 py-2 text-xs text-white/75">Bấm thiết bị để điều khiển · Kéo chuột trái để xoay · Chuột phải để dịch chuyển · Cuộn để tiến/lùi</div>
          <div className="flex min-h-0 flex-1 flex-col md:flex-row">
          <div className="relative min-h-64 min-w-0 flex-1">
            <iframe ref={iframeRef} title="Mô hình nhà 3D" src="/unity/index.html" onLoad={() => iframeRef.current?.contentWindow?.postMessage({ type: 'homate:request-ready' }, window.location.origin)} className="h-full w-full border-0" allow="fullscreen; gamepad; autoplay" allowFullScreen />
            <div className="absolute bottom-3 left-3 flex gap-1 rounded-xl bg-white p-1 shadow-lg" aria-label="Thu phóng mô hình">
              {(['in', 'out'] as const).map(direction => <button key={direction} type="button" disabled={!runtimeReady}
                aria-label={direction === 'in' ? 'Phóng to' : 'Thu nhỏ'}
                onClick={() => {
                  iframeRef.current?.contentWindow?.postMessage({ type: 'homate:zoom', direction }, window.location.origin)
                  iframeRef.current?.contentWindow?.focus()
                }}
                className="h-10 w-10 rounded-lg text-2xl text-[#1E4D38] hover:bg-[#EFF5F0] disabled:opacity-40">{direction === 'in' ? '+' : '−'}</button>)}
            </div>
          </div>
          {selectedDevice && <SimulationDevicePanel key={selectedDevice.id} device={selectedDevice} onClose={() => selectDevice('')}
            onApplied={() => iframeRef.current?.contentWindow?.focus()} />}
          </div>
        </>
      ) : (
        <div className="m-auto max-w-md px-6 py-10 text-center text-white">
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-white/20 bg-white/5 text-3xl" aria-hidden="true">⌂</div>
          <h2 className="text-lg font-semibold">{status === 'loading' ? 'Đang kiểm tra mô hình…' : 'Mô hình 3D chưa sẵn sàng'}</h2>
          {status === 'unavailable' && <>
            <p className="mt-2 text-sm leading-relaxed text-white/65">Bản mô hình chưa được tải lên. Các tính năng điều khiển nhà vẫn dùng bình thường.</p>
            <button type="button" className="mt-5 rounded-lg border border-white/25 px-4 py-2 text-sm hover:bg-white/10" onClick={() => { setStatus('loading'); setAttempt(value => value + 1) }}>Kiểm tra lại</button>
          </>}
        </div>
      )}
    </section>
  )
}
