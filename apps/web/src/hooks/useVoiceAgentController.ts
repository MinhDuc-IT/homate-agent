import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { apiFetch } from '@/api/http'
import { API_HITL } from '@/config/api'
import { fetchHomeSettings } from '@/api/settings'
import { useDevices } from '@/context/DevicesContext'
import { useToast } from '@/context/ToastContext'
import { useAgentTrace } from '@/hooks/useAgentTrace'
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder'
import { useVoiceSession } from '@/hooks/useVoiceSession'
import { playBase64Audio } from '@/utils/audioWav'
import { deriveVoiceAgentState } from '@/utils/voiceAgentState'
import type { AmbientSuggestion } from '@/types/ambient'

const HITL_TIMEOUT_SECONDS = 30

export type PendingMode = 'idle' | 'clarify' | 'hitl' | 'ambient'

export type AgentResult = {
  response: string
  transcript?: string
  intent?: string
  needs_clarify?: boolean
  needs_hitl?: boolean
  session_id?: string
  clarify_question?: string
  hitl_request_id?: string
  hitl_action_summary?: string
}

export function useVoiceAgentController() {
  const { showToast } = useToast()
  const { refresh, respondAmbientSuggestion } = useDevices()
  const { status: wsStatus, sessionId, sendAudio, sendJson } = useVoiceSession()
  const { events: traceEvents, status: traceStatus, clear: clearTrace } =
    useAgentTrace(sessionId)
  const { recording, error: micError, start, stop, cancel } = useVoiceRecorder()
  const [busy, setBusy] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [last, setLast] = useState<AgentResult | null>(null)
  const [pendingMode, setPendingMode] = useState<PendingMode>('idle')
  const [hitlRequestId, setHitlRequestId] = useState('')
  const [hitlSummary, setHitlSummary] = useState('')
  const [clarifyQuestion, setClarifyQuestion] = useState('')
  const [secondsLeft, setSecondsLeft] = useState(HITL_TIMEOUT_SECONDS)
  const [hitlTimeoutSeconds, setHitlTimeoutSeconds] = useState(HITL_TIMEOUT_SECONDS)
  const hitlExpiredRef = useRef(false)
  const hitlResolvingRef = useRef(false)
  const busyRef = useRef(false)
  const hitlRequestIdRef = useRef('')
  const pendingModeRef = useRef<PendingMode>('idle')

  busyRef.current = busy
  hitlRequestIdRef.current = hitlRequestId
  pendingModeRef.current = pendingMode

  const agentState = useMemo(
    () => deriveVoiceAgentState(wsStatus, recording, busy, speaking),
    [wsStatus, recording, busy, speaking],
  )

  useEffect(() => {
    let cancelled = false
    void fetchHomeSettings()
      .then((settings) => {
        if (!cancelled) setHitlTimeoutSeconds(settings.hitl_timeout_seconds)
      })
      .catch(() => undefined)
    const updateTimeout = (event: Event) => {
      const value = (event as CustomEvent<{ timeoutSeconds?: number }>).detail?.timeoutSeconds
      if (typeof value === 'number') setHitlTimeoutSeconds(value)
    }
    window.addEventListener('hitl.settings.updated', updateTimeout)
    return () => {
      cancelled = true
      window.removeEventListener('hitl.settings.updated', updateTimeout)
    }
  }, [])

  const clearPending = useCallback(async () => {
    const requestId = hitlRequestIdRef.current
    const mode = pendingModeRef.current
    hitlResolvingRef.current = true
    hitlExpiredRef.current = true
    setPendingMode('idle')
    setHitlRequestId('')
    setHitlSummary('')
    setClarifyQuestion('')
    setSecondsLeft(HITL_TIMEOUT_SECONDS)
    try {
      if (mode === 'hitl' && requestId) {
        await apiFetch(`${API_HITL}/confirm`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ request_id: requestId, approved: false }),
        })
      } else if (mode === 'ambient' && requestId) {
        await respondAmbientSuggestion(requestId, false)
      }
    } catch {
      /* best-effort reject */
    }
    try {
      await sendJson({ type: 'cancel_pending' })
    } catch {
      /* ignore if WS closed */
    }
  }, [respondAmbientSuggestion, sendJson])

  useEffect(() => {
    const receiveSuggestion = (event: Event) => {
      const suggestion = (event as CustomEvent<AmbientSuggestion>).detail
      if (!suggestion?.request_id) return
      hitlExpiredRef.current = false
      hitlResolvingRef.current = false
      setPendingMode('ambient')
      setHitlRequestId(suggestion.request_id)
      setHitlSummary(suggestion.message)
      setClarifyQuestion('')
      setSecondsLeft(suggestion.expires_in_seconds)
      setLast({
        response: suggestion.message,
        intent: 'ambient_confirmation_required',
        session_id: sessionId || undefined,
      })
      void sendJson({ type: 'await_ambient', request_id: suggestion.request_id })
    }
    window.addEventListener('ambient.suggestion', receiveSuggestion)
    return () => window.removeEventListener('ambient.suggestion', receiveSuggestion)
  }, [sendJson, sessionId])

  useEffect(() => {
    if (!['hitl', 'ambient'].includes(pendingMode) || !hitlRequestId) return
    hitlExpiredRef.current = false
    hitlResolvingRef.current = false
    const timeoutSeconds = pendingMode === 'ambient' ? 60 : hitlTimeoutSeconds
    setSecondsLeft(timeoutSeconds)

    // Pause wall-clock while busy/resolving so voice confirm cannot race timeout.
    let remainingMs = timeoutSeconds * 1000
    let lastTick = Date.now()
    const requestIdAtStart = hitlRequestId

    const tick = window.setInterval(() => {
      const now = Date.now()
      const paused = busyRef.current || hitlResolvingRef.current
      if (!paused) {
        remainingMs -= now - lastTick
      }
      lastTick = now
      const left = Math.max(Math.ceil(remainingMs / 1000), 0)
      setSecondsLeft(left)

      if (left > 0 || hitlExpiredRef.current || hitlResolvingRef.current) return
      if (busyRef.current) return
      if (hitlRequestIdRef.current !== requestIdAtStart) return

      hitlExpiredRef.current = true
      hitlResolvingRef.current = true
      window.clearInterval(tick)
      void (async () => {
        try {
          if (pendingMode === 'ambient') {
            await respondAmbientSuggestion(requestIdAtStart, false)
          } else {
            await apiFetch(`${API_HITL}/confirm`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                request_id: requestIdAtStart,
                approved: false,
              }),
            })
          }
        } catch {
          /* best-effort cancel */
        }
        if (hitlRequestIdRef.current !== requestIdAtStart) return
        setLast({
          response:
            'Hết thời gian xác nhận — yêu cầu đã hủy. Nói lại lệnh nếu cần.',
          intent: 'hitl_timeout',
        })
        setPendingMode('idle')
        setHitlRequestId('')
        setHitlSummary('')
        showToast('Hết thời gian xác nhận', 'warning')
        try {
          await sendJson({ type: 'cancel_pending' })
        } catch {
          /* ignore */
        }
      })()
    }, 250)

    return () => window.clearInterval(tick)
  }, [pendingMode, hitlRequestId, hitlTimeoutSeconds, respondAmbientSuggestion, sendJson, showToast])

  const applyResult = useCallback(
    async (data: AgentResult) => {
      setLast(data)
      window.setTimeout(() => {
        void refresh()
      }, 600)

      if (data.needs_hitl && data.hitl_request_id) {
        hitlResolvingRef.current = false
        hitlExpiredRef.current = false
        setPendingMode('hitl')
        setHitlRequestId(data.hitl_request_id)
        setHitlSummary(data.hitl_action_summary || data.response)
        setClarifyQuestion('')
        try {
          await sendJson({
            type: 'await_hitl',
            request_id: data.hitl_request_id,
          })
        } catch (err) {
          showToast(
            err instanceof Error ? err.message : 'Không bật chế độ HITL voice',
            'error',
          )
        }
        return
      }

      // Resolved HITL / normal reply — stop any in-flight countdown.
      hitlResolvingRef.current = true
      if (data.needs_clarify) {
        setPendingMode('clarify')
        setClarifyQuestion(data.clarify_question || data.response)
        setHitlRequestId('')
        setHitlSummary('')
        return
      }

      setPendingMode('idle')
      setHitlRequestId('')
      setHitlSummary('')
      setClarifyQuestion('')
    },
    [refresh, sendJson, showToast],
  )

  async function playReply(audioFormat?: string, audioBase64?: string) {
    if (!audioBase64) return
    setSpeaking(true)
    try {
      await playBase64Audio(audioFormat, audioBase64)
    } catch {
      /* TTS mock có thể không phát được */
    } finally {
      setSpeaking(false)
    }
  }

  async function runVoicePipeline(wavBytes: Uint8Array) {
    setBusy(true)
    // Freeze HITL countdown while this confirmation utterance is processed.
    if (pendingModeRef.current === 'hitl' || pendingModeRef.current === 'ambient') {
      hitlResolvingRef.current = true
    }
    clearTrace()
    try {
      if (pendingMode === 'hitl' && hitlRequestId) {
        await sendJson({ type: 'await_hitl', request_id: hitlRequestId })
      } else if (pendingMode === 'ambient' && hitlRequestId) {
        await sendJson({ type: 'await_ambient', request_id: hitlRequestId })
      }

      const data = await sendAudio(wavBytes)
      const transcript = (data.text || '').trim()
      const result: AgentResult = {
        response: data.reply || '',
        transcript,
        intent: data.intent,
        needs_clarify: data.needs_clarify,
        needs_hitl: data.needs_hitl,
        session_id: data.session_id,
        clarify_question: data.clarify_question,
        hitl_request_id: data.hitl_request_id,
        hitl_action_summary: data.hitl_action_summary,
      }
      await applyResult(result)
      await playReply(data.audio_format, data.audio_base64)
    } catch (err) {
      // Allow timeout again if confirmation failed to send.
      if (pendingModeRef.current === 'hitl' || pendingModeRef.current === 'ambient') {
        hitlResolvingRef.current = false
      }
      const msg = err instanceof Error ? err.message : 'Voice pipeline lỗi'
      showToast(msg, 'error')
    } finally {
      setBusy(false)
    }
  }

  async function toggleMic() {
    if (busy || speaking) return

    if (wsStatus !== 'open') {
      showToast(
        'Voice WebSocket chưa sẵn sàng — kiểm tra backend :8000',
        'error',
      )
      return
    }

    if (recording) {
      const wav = await stop()
      if (!wav || wav.length === 0) {
        showToast(
          'Không ghi được audio — nói lâu hơn 1 giây rồi nhấn lại để gửi',
          'warning',
        )
        return
      }
      await runVoicePipeline(wav)
      return
    }

    const ok = await start()
    if (ok) {
      const hint =
        pendingMode === 'clarify'
          ? 'Đang nghe câu trả lời… nhấn lại để gửi'
            : pendingMode === 'hitl' || pendingMode === 'ambient'
            ? 'Nói xác nhận hoặc hủy — nhấn lại để gửi'
            : 'Đang nghe… nhấn aura lần nữa để gửi'
      showToast(hint, 'info')
    } else {
      showToast(micError || 'Không mở được micro', 'error')
    }
  }

  const actionLabel =
    agentState === 'listening' && recording
      ? 'Nhấn để gửi'
      : agentState === 'thinking'
        ? 'Đang xử lý…'
        : agentState === 'speaking'
          ? 'Đang phát âm thanh…'
          : agentState === 'connecting'
            ? 'Đang kết nối…'
            : pendingMode === 'clarify'
              ? 'Nhấn để trả lời bằng giọng nói'
              : pendingMode === 'hitl' || pendingMode === 'ambient'
                ? 'Nhấn để nói đồng ý / hủy'
                : 'Nhấn để nói'

  const footerPrompt =
    pendingMode === 'clarify'
      ? clarifyQuestion || 'Cần làm rõ thêm — hãy trả lời bằng giọng nói.'
      : pendingMode === 'hitl' || pendingMode === 'ambient'
        ? busy
          ? `${hitlSummary || 'Cần xác nhận'} — đang xử lý xác nhận…`
          : `${hitlSummary || 'Cần xác nhận'} — nói xác nhận/hủy tự nhiên (${secondsLeft}s).`
        : null

  return {
    wsStatus,
    agentState,
    recording,
    busy,
    speaking,
    micError,
    last,
    pendingMode,
    secondsLeft,
    footerPrompt,
    actionLabel,
    traceEvents,
    traceStatus,
    toggleMic,
    cancel,
    clearPending,
  }
}
