import { KnowledgeSources } from '@/components/assistant/KnowledgeSources'
import type { KnowledgeSource } from '@/api/knowledge'
import { useEffect, useRef, useState } from 'react'
import { MicrophoneButton } from '@/components/homemind/VoiceMicrophone'
import { ActionCard } from '@/components/assistant/ActionCard'
import { actionStatusLabels } from '@/components/assistant/actionStatus'
import { apiFetch, parseError } from '@/api/http'
import { sendChat, decideAction, type ChatMessage, type PendingAction } from '@/api/agent'
import { useDevices } from '@/context/DevicesContext'
import { cn } from '@/utils/cn'

/** Global push-to-talk voice assistant, using the original header Aura. */
export function VoiceDock({ variant = 'footer', className }: { variant?: 'footer' | 'header'; className?: string }) {
  const [busy, setBusy] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [micActive, setMicActive] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [reply, setReply] = useState('')
  const [sources, setSources] = useState<KnowledgeSource[]>([])
  const [error, setError] = useState('')
  const [actions, setActions] = useState<PendingAction[]>([])
  const [trace, setTrace] = useState<{ tool: string; status: string }[]>([])
  const history = useRef<ChatMessage[]>([])
  const audio = useRef<HTMLAudioElement | null>(null)
  const audioUrl = useRef('')
  const generation = useRef(0)
  const inFlight = useRef(false)
  const mounted = useRef(false)
  const { ambientSuggestions, respondAmbientSuggestion } = useDevices()
  const suggestion = ambientSuggestions[0]

  function stopAudio() {
    audio.current?.pause(); audio.current = null
    if (audioUrl.current) URL.revokeObjectURL(audioUrl.current)
    audioUrl.current = ''
  }
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; stopAudio() }
  }, [])

  async function speak(text: string) {
    const current = ++generation.current
    stopAudio()
    try {
      const response = await apiFetch('/api/ai/speech/synthesize', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: text.slice(0, 4000) }) })
      if (!response.ok) throw new Error(await parseError(response))
      const blob = await response.blob()
      if (!mounted.current || current !== generation.current) return
      audioUrl.current = URL.createObjectURL(blob)
      const player = new Audio(audioUrl.current); audio.current = player
      player.onended = () => { stopAudio(); if (mounted.current) setSpeaking(false) }
      player.onerror = () => { stopAudio(); if (mounted.current) { setSpeaking(false); setError('Không phát được giọng đọc. Phản hồi vẫn hiển thị bên dưới.') } }
      await player.play()
      if (mounted.current && current === generation.current) setSpeaking(true)
    } catch (err) {
      if (mounted.current && current === generation.current) {
        stopAudio(); setSpeaking(false)
        setError(err instanceof Error ? err.message : 'Không phát được giọng đọc.')
      }
    }
  }

  async function sendVoice(text: string) {
    if (inFlight.current) return
    inFlight.current = true; setBusy(true); setError(''); setTranscript(text); setReply(''); setSources([])
    try {
      const response = await sendChat(text, history.current, crypto.randomUUID())
      if (!mounted.current) return
      history.current = [...history.current, { role: 'user' as const, content: text }, { role: 'assistant' as const, content: response.reply }].slice(-12)
      setSources(response.sources ?? []); setReply(response.reply); setActions(previous => [...previous, ...response.pending_actions]); setTrace(response.trace)
      await speak(response.reply)
    } catch (err) {
      if (mounted.current) setError(err instanceof Error ? err.message : 'Không xử lý được câu lệnh. Hãy kiểm tra trạng thái trước khi thử lại.')
    } finally {
      inFlight.current = false; if (mounted.current) setBusy(false)
    }
  }

  async function decide(action: PendingAction, approved: boolean) {
    if (inFlight.current) return
    inFlight.current = true; setBusy(true); setError('')
    try {
      const result = await decideAction(action.id, approved)
      if (!mounted.current) return
      setActions(previous => previous.map(item => item.id === action.id ? result : item))
      const message = `${action.summary}: ${actionStatusLabels[result.status] ?? result.status}.`
      setReply(message)
      history.current = [...history.current, { role: 'assistant' as const, content: message }].slice(-12)
      await speak(message)
    } catch (err) { if (mounted.current) setError(err instanceof Error ? err.message : 'Không xử lý được xác nhận.') }
    finally { inFlight.current = false; if (mounted.current) setBusy(false) }
  }

  return <section aria-label="Hội thoại giọng nói" className={cn('min-w-0 flex-1', variant === 'footer' && 'border-t border-border p-3', className)}>
    <div className="flex min-w-0 items-center gap-2">
      <MicrophoneButton disabled={busy || speaking} speaking={speaking} pending={actions.some(action => action.status === 'pending')} onActiveChange={setMicActive} onTranscript={value => void sendVoice(value)} />
      <div className="min-w-0 flex-1 text-left">
        <span className="block text-[10px] font-semibold tracking-widest text-primary">{speaking ? 'ĐANG TRẢ LỜI' : busy ? 'ĐANG XỬ LÝ' : micActive ? 'ĐANG NGHE / NHẬN DẠNG' : 'TRỢ LÝ GIỌNG NÓI'}</span>
        <div role="log" aria-label="Nội dung giọng nói" aria-live="polite" className="max-h-24 space-y-0.5 overflow-y-auto break-words pr-1 text-[11px] leading-snug [overflow-wrap:anywhere]">
          {transcript ? <p className="text-text-secondary">Bạn: {transcript}</p> : <p className="text-text-muted">Nhấn Aura để nói · nhấn lại để gửi</p>}
          {reply && <p className="whitespace-pre-wrap text-text-primary">HomeMate: {reply}</p>}
          {busy && !reply && <p role="status" className="text-primary">Đang xử lý…</p>}
          {error && <p role="alert" className="text-danger">{error}</p>}
        </div>
      </div>
      {(busy || speaking) && <button type="button" onClick={() => { generation.current++; stopAudio(); setSpeaking(false) }} className="shrink-0 text-xs text-primary">Dừng đọc</button>}
    </div>
    <div className="max-h-56 min-w-0 overflow-y-auto">
      <KnowledgeSources sources={sources} />
      {actions.map(action => <ActionCard key={action.id} action={action} disabled={busy || micActive} processing={busy} onDecide={(item, approved) => void decide(item, approved)} />)}
      {suggestion && <div className="mt-3 rounded-lg bg-amber-50 p-2 text-xs"><p>{suggestion.message}</p><button type="button" className="mr-3 mt-2 text-primary" onClick={() => void respondAmbientSuggestion(suggestion.request_id, true)}>Tắt thiết bị</button><button type="button" onClick={() => void respondAmbientSuggestion(suggestion.request_id, false)}>Bỏ qua</button></div>}
      {trace.length > 0 && <details className="mt-3 text-xs text-text-muted"><summary>Agent trace</summary>{trace.map((item, index) => <p key={index}>{item.tool}: {item.status}</p>)}</details>}
    </div>
  </section>
}
