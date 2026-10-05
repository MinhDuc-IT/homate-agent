import { useNavigate } from 'react-router-dom'
import { AgentAudioVisualizerAura } from '@/components/agents-ui/agent-audio-visualizer-aura'
import { AgentTracePanel } from '@/components/homemind/AgentTracePanel'
import { Button } from '@/components/ui/Button'
import { ROUTES } from '@/config/routes'
import { useVoiceAgentController } from '@/hooks/useVoiceAgentController'
import { cn } from '@/utils/cn'
import { VOICE_AGENT_STATE_LABEL } from '@/utils/voiceAgentState'

/** Full-screen voice agent (optional / debug). Main UX lives in VoiceDock. */
export function VoiceAgentPage() {
  const navigate = useNavigate()
  const {
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
  } = useVoiceAgentController()

  return (
    <div className="fixed inset-0 z-50 flex flex-col overflow-hidden bg-[#070a0f] text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(31,213,249,0.12),transparent_55%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,transparent,rgba(0,0,0,0.45)_75%)]" />

      <header className="relative z-10 flex items-center justify-between px-4 py-4 sm:px-6">
        <button
          type="button"
          onClick={() => navigate(ROUTES.dashboard)}
          className="rounded-lg px-3 py-2 text-sm text-white/70 transition hover:bg-white/5 hover:text-white"
        >
          ← Về nhà
        </button>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => navigate(ROUTES.voice)}
            className="rounded-lg px-3 py-2 text-xs text-white/50 transition hover:bg-white/5 hover:text-white/80"
          >
            Demo / Text
          </button>
          <span
            className={cn(
              'rounded-full px-2.5 py-1 text-[10px] font-medium tracking-wide',
              wsStatus === 'open'
                ? 'bg-emerald-400/10 text-emerald-300'
                : 'bg-white/5 text-white/45',
            )}
          >
            WS {wsStatus}
          </span>
        </div>
      </header>

      <main className="relative z-10 flex flex-1 flex-col items-center justify-start overflow-y-auto px-4 pb-8 pt-4">
        <div className="mb-6 flex flex-wrap justify-center gap-2">
          {(['connecting', 'listening', 'thinking', 'speaking'] as const).map(
            (state) => (
              <span
                key={state}
                className={cn(
                  'rounded-full px-3 py-1 text-[10px] font-semibold tracking-[0.18em]',
                  agentState === state
                    ? 'bg-cyan-400/15 text-cyan-300 ring-1 ring-cyan-400/30'
                    : 'text-white/30',
                )}
              >
                {VOICE_AGENT_STATE_LABEL[state]}
              </span>
            ),
          )}
        </div>

        {pendingMode !== 'idle' ? (
          <div
            className={cn(
              'mb-5 max-w-lg rounded-2xl border px-4 py-3 text-center',
              pendingMode === 'hitl'
                ? 'border-amber-400/30 bg-amber-400/10 text-amber-100'
                : 'border-cyan-400/30 bg-cyan-400/10 text-cyan-100',
            )}
          >
            <p className="text-[10px] font-semibold tracking-[0.2em] opacity-80">
              {pendingMode === 'hitl'
                ? 'CẦN XÁC NHẬN (VOICE)'
                : 'CẦN LÀM RÕ (VOICE)'}
            </p>
            <p className="mt-1 text-sm">{footerPrompt}</p>
            {pendingMode === 'hitl' ? (
              <p className="mt-2 text-xs text-amber-200/70">
                Còn {secondsLeft}s
              </p>
            ) : null}
            <button
              type="button"
              className="mt-3 text-xs text-white/50 underline-offset-2 hover:text-white/80 hover:underline"
              onClick={() => void clearPending()}
            >
              Hủy và nói lệnh mới
            </button>
          </div>
        ) : null}

        <button
          type="button"
          disabled={busy || speaking || wsStatus !== 'open'}
          onClick={() => void toggleMic()}
          className={cn(
            'flex w-full max-w-lg flex-col items-center justify-center transition',
            (busy || speaking || wsStatus !== 'open') &&
              'cursor-not-allowed opacity-80',
            recording && 'scale-[0.98]',
          )}
          aria-label={actionLabel}
        >
          <div className="aspect-square w-[min(72vw,28rem)]">
            <AgentAudioVisualizerAura
              size="xl"
              state={agentState}
              color={pendingMode === 'hitl' ? '#FBBF24' : '#1FD5F9'}
              colorShift={0.3}
              themeMode="dark"
              className="h-full w-full"
            />
          </div>
          <p className="mt-6 text-xs font-semibold tracking-[0.24em] text-cyan-300">
            {VOICE_AGENT_STATE_LABEL[agentState] || agentState.toUpperCase()}
          </p>
          <p className="mt-2 text-sm text-white/65">{actionLabel}</p>
          {recording ? (
            <p className="mt-1 animate-pulse text-xs font-medium text-red-300">
              ● REC — nhấn lại aura để gửi
            </p>
          ) : null}
        </button>

        {wsStatus !== 'open' ? (
          <p className="mt-4 text-center text-xs text-amber-300/90">
            {wsStatus === 'connecting'
              ? 'Đang kết nối WebSocket…'
              : 'WebSocket chưa kết nối — cần Gateway :8000'}
          </p>
        ) : null}

        {recording ? (
          <Button
            variant="ghost"
            size="sm"
            className="mt-5 text-white/70 hover:bg-white/5 hover:text-white"
            disabled={busy}
            onClick={(event) => {
              event.stopPropagation()
              cancel()
            }}
          >
            Huỷ ghi âm
          </Button>
        ) : null}
        {micError ? <p className="mt-3 text-xs text-red-400">{micError}</p> : null}
        <div className="mt-6 w-full max-w-lg">
          <AgentTracePanel events={traceEvents} status={traceStatus} dark />
        </div>
      </main>

      <footer className="relative z-10 border-t border-white/10 bg-black/25 px-4 py-5 backdrop-blur-md sm:px-6">
        {busy ? (
          <p className="mx-auto max-w-2xl text-center text-sm text-cyan-200/80">
            Đang xử lý (STT → Agent)…
          </p>
        ) : last ? (
          <div className="mx-auto max-w-2xl space-y-2">
            {last.transcript !== undefined ? (
              <p className="text-sm text-white/55">
                Bạn:{' '}
                <span className="text-white/90">{last.transcript || '—'}</span>
              </p>
            ) : null}
            <p className="text-base text-white/90">{last.response}</p>
            {last.intent ? (
              <p className="text-xs text-white/40">Intent: {last.intent}</p>
            ) : null}
          </div>
        ) : (
          <p className="mx-auto max-w-2xl text-center text-sm text-white/45">
            Nói lệnh tiếng Việt — ví dụ «Bật đèn phòng khách»
          </p>
        )}
      </footer>
    </div>
  )
}
