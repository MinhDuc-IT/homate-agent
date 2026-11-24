import { useEffect, useRef, useState } from 'react'
import { cn } from '@/utils/cn'

type ViewOption = { id: string; label: string }

export function UnityViewport({ className }: { className?: string }) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'unavailable'>('loading')
  const [attempt, setAttempt] = useState(0)
  const [views, setViews] = useState<ViewOption[]>([])
  const [runtimeReady, setRuntimeReady] = useState(false)
  const [selectedView, setSelectedView] = useState('overview')
  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin || event.source !== iframeRef.current?.contentWindow) return
      if (event.data?.type === 'homate:ready') setRuntimeReady(true)
      if (event.data?.type === 'homate:view-changed' && views.some(view => view.id === event.data.viewId)) {
        setSelectedView(event.data.viewId)
      }
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [views])
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
          {views.length > 0 && <nav aria-label="Góc nhìn ngôi nhà" className="flex shrink-0 items-center gap-2 overflow-x-auto border-b border-[#DCE6DF] bg-white p-3">
            {views.map(view => <button key={view.id} type="button" disabled={!runtimeReady}
              aria-pressed={selectedView === view.id}
              onClick={() => iframeRef.current?.contentWindow?.postMessage({ type: 'homate:set-view', viewId: view.id }, window.location.origin)}
              className={cn('shrink-0 rounded-lg px-3 py-2 text-sm font-medium transition-colors disabled:cursor-wait disabled:opacity-50',
                selectedView === view.id ? 'bg-[#1E4D38] text-white' : 'bg-[#EFF5F0] text-[#1E4D38] hover:bg-[#DDEBDF]')}>
              {view.label}
            </button>)}
            {!runtimeReady && <span role="status" className="shrink-0 text-xs text-[#66746A]">Đang tải mô hình…</span>}
          </nav>}
          <div className="min-h-0 flex-1">
            <iframe ref={iframeRef} title="Mô hình nhà 3D" src="/unity/index.html" className="h-full w-full border-0" allow="fullscreen; gamepad" allowFullScreen />
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
