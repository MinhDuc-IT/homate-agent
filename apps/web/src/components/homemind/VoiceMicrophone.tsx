import { useEffect, useRef, useState } from 'react'
import { apiFetch, readJson } from '@/api/http'
import { AgentAudioVisualizerAura } from '@/components/agents-ui/agent-audio-visualizer-aura'

function wav(samples: Float32Array[], rate: number): Blob {
  const length = samples.reduce((total, part) => total + part.length, 0)
  const buffer = new ArrayBuffer(44 + length * 2)
  const view = new DataView(buffer)
  const text = (offset: number, value: string) => [...value].forEach((char, i) => view.setUint8(offset + i, char.charCodeAt(0)))
  text(0, 'RIFF'); view.setUint32(4, 36 + length * 2, true); text(8, 'WAVE'); text(12, 'fmt ')
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true)
  view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true)
  text(36, 'data'); view.setUint32(40, length * 2, true)
  let offset = 44
  for (const part of samples) for (const value of part) {
    const sample = Math.max(-1, Math.min(1, value))
    view.setInt16(offset, sample * (sample < 0 ? 32768 : 32767), true); offset += 2
  }
  return new Blob([buffer], { type: 'audio/wav' })
}

export function MicrophoneButton({ disabled, speaking, pending, onTranscript, onActiveChange }: { disabled: boolean; speaking: boolean; pending: boolean; onTranscript: (text: string) => void; onActiveChange: (active: boolean) => void }) {
  const [state, setState] = useState<'idle' | 'starting' | 'recording' | 'processing'>('idle')
  const [error, setError] = useState('')
  const stopRef = useRef<(() => void) | null>(null)
  const active = useRef(false)
  useEffect(() => {
    active.current = true
    return () => { active.current = false; stopRef.current?.() }
  }, [])
  async function start() {
    if (!navigator.mediaDevices?.getUserMedia) { setError('Micro cần HTTPS hoặc localhost và trình duyệt hỗ trợ thu âm.'); return }
    setState('starting'); setError(''); onActiveChange(true)
    let stream: MediaStream | undefined
    let context: AudioContext | undefined
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true }, video: false })
      if (!active.current) { stream.getTracks().forEach(track => track.stop()); return }
      context = new AudioContext()
      await context.resume()
      if (!active.current) { stream.getTracks().forEach(track => track.stop()); void context.close(); return }
      const source = context.createMediaStreamSource(stream)
      // PCM WAV also works with local STT engines that cannot decode WebM.
      const processor = context.createScriptProcessor(4096, 1, 1)
      const silence = context.createGain(); silence.gain.value = 0
      const parts: Float32Array[] = []
      let count = 0
      const rate = context.sampleRate
      processor.onaudioprocess = event => {
        const part = new Float32Array(event.inputBuffer.getChannelData(0))
        parts.push(part); count += part.length
        if (count >= rate * 60) stopRef.current?.()
      }
      source.connect(processor); processor.connect(silence); silence.connect(context.destination)
      const timer = window.setTimeout(() => stopRef.current?.(), 60_000)
      stopRef.current = () => {
        stopRef.current = null; window.clearTimeout(timer)
        processor.onaudioprocess = null; source.disconnect(); processor.disconnect(); silence.disconnect()
        stream?.getTracks().forEach(track => track.stop()); void context?.close()
        if (!active.current) return
        setState('processing')
        void (async () => {
          try {
            const result = await readJson<{ text: string }>(await apiFetch('/api/ai/speech/transcribe', { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: wav(parts, rate) }))
            if (active.current) {
              if (result.text) onTranscript(result.text)
              else setError('Chưa nghe rõ. Hãy thử nói lại.')
            }
          } catch (err) { if (active.current) setError(err instanceof Error ? err.message : 'Không nhận dạng được giọng nói.') }
          finally { if (active.current) { setState('idle'); onActiveChange(false) } }
        })()
      }
      setState('recording')
    } catch {
      stream?.getTracks().forEach(track => track.stop()); void context?.close()
      if (active.current) { onActiveChange(false); setState('idle'); setError('Không mở được micro. Hãy kiểm tra quyền truy cập micro.') }
    }
  }
  return <div className="shrink-0 text-xs">
    <button type="button" disabled={disabled || state === 'starting' || state === 'processing'} onClick={() => state === 'recording' ? stopRef.current?.() : void start()} aria-label={state === 'recording' ? 'Dừng và gửi lệnh giọng nói' : 'Bắt đầu nói với HomeMate'} aria-pressed={state === 'recording'} className={`h-10 w-10 overflow-hidden rounded-full disabled:opacity-60 ${state === 'recording' ? 'ring-2 ring-red-400' : ''}`}>
      <AgentAudioVisualizerAura size="sm" state={speaking ? 'speaking' : disabled || state === 'processing' || state === 'starting' ? 'thinking' : 'listening'} color={pending ? '#FBBF24' : '#22C55E'} colorShift={0.2} themeMode="light" className="h-full w-full" />
    </button>
    {state === 'recording' && <span role="status" className="ml-2">Đang thu âm · tối đa 60 giây</span>}
    {error && <p role="alert" className="mt-1 text-danger">{error}</p>}
  </div>
}
