import { useState } from 'react'
import { CloseIcon } from '@/assets/icons/CommonIcons'
import { AgentAudioVisualizerAura } from '@/components/agents-ui/agent-audio-visualizer-aura'
import { AgentTracePanel } from '@/components/homemind/AgentTracePanel'
import { Button } from '@/components/ui/Button'
import { useVoiceAgentController } from '@/hooks/useVoiceAgentController'
import { cn } from '@/utils/cn'
import { VOICE_AGENT_STATE_LABEL } from '@/utils/voiceAgentState'
import { AI_ENABLED } from '@/config/features'
import { useDevices } from '@/context/DevicesContext'

type VoiceDockVariant = 'footer' | 'header'

interface VoiceDockProps {
  variant?: VoiceDockVariant
  className?: string
}

/** Compact voice control dock for panel shell or header bar. */
export function VoiceDock({ variant = 'footer', className }: VoiceDockProps) {
  if (AI_ENABLED) return <ConnectedVoiceDock variant={variant} className={className} />
  return <SoftwareDock variant={variant} className={className} />
}

function SoftwareDock({ variant, className }: VoiceDockProps) {
  const { ambientSuggestions, respondAmbientSuggestion } = useDevices()
  const suggestion = ambientSuggestions[0]
  return <div className={cn('flex min-w-0 items-center gap-3 rounded-xl px-3 py-2', variant === 'footer' && 'border-t border-sidebar-border bg-elevated', className)}>
    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-subtle text-primary" aria-hidden="true">✦</div>
    <div className="min-w-0 flex-1"><p className="text-xs font-semibold text-primary">{suggestion ? 'Gợi ý tiết kiệm điện' : 'Trợ lý HomeMate'}</p><p className="mt-0.5 text-[11px] text-text-secondary">{suggestion?.message ?? 'AI sẽ được tích hợp ở giai đoạn tiếp theo.'}</p></div>
    {suggestion && <div className="flex shrink-0 gap-2"><Button size="xs" onClick={() => void respondAmbientSuggestion(suggestion.request_id, true)}>Tắt thiết bị</Button><Button size="xs" variant="ghost" onClick={() => void respondAmbientSuggestion(suggestion.request_id, false)}>Bỏ qua</Button></div>}
  </div>
}

function ConnectedVoiceDock({ variant = 'footer', className }: VoiceDockProps) {
  const isHeader = variant === 'header'
  const [traceOpen, setTraceOpen] = useState(false)
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
    <div
      className={cn(
        'relative shrink-0',
        isHeader
          ? 'min-w-0 flex-1 bg-transparent'
          : 'border-t border-sidebar-border bg-elevated/95 backdrop-blur-md',
        className,
      )}
    >
      {traceOpen ? (
        <div
          className={cn(
            'absolute inset-x-0 z-30 overflow-hidden rounded-xl border border-primary/15 bg-surface shadow-elevated',
            isHeader
              ? 'top-[calc(100%+0.5rem)]'
              : 'bottom-[calc(100%+0.5rem)] inset-x-2',
          )}
        >
          <div className="flex items-center justify-between gap-2 border-b border-border-light bg-surface-subtle px-3 py-2">
            <p className="text-[11px] font-semibold tracking-wide text-primary">
              Agent trace
            </p>
            <button
              type="button"
              className="flex h-6 w-6 items-center justify-center rounded-md text-text-muted transition hover:bg-primary-subtle hover:text-primary"
              aria-label="Đóng agent trace"
              onClick={() => setTraceOpen(false)}
            >
              <CloseIcon className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="p-2">
            <AgentTracePanel
              events={traceEvents}
              status={traceStatus}
              listClassName="max-h-48"
            />
          </div>
        </div>
      ) : null}

      {pendingMode !== 'idle' ? (
        <div
          className={cn(
            'px-3 py-1.5 text-xs',
            isHeader ? 'rounded-xl' : 'border-b',
            pendingMode === 'hitl' || pendingMode === 'ambient'
              ? 'border-amber-400/20 bg-amber-400/10 text-amber-800'
              : 'border-emerald-400/20 bg-emerald-400/10 text-emerald-900',
          )}
        >
          <div className="flex items-start justify-between gap-2">
            <p className="leading-snug">{footerPrompt}</p>
            {pendingMode === 'hitl' || pendingMode === 'ambient' ? (
              <span className="shrink-0 text-amber-700/70">{secondsLeft}s</span>
            ) : null}
          </div>
          <button
            type="button"
            className="mt-0.5 text-[11px] text-[#1E4D38] underline-offset-2 hover:underline"
            onClick={() => void clearPending()}
          >
            Hủy
          </button>
        </div>
      ) : null}

      <div
        className={cn(
          'flex items-center gap-2 sm:gap-3',
          isHeader ? 'px-0 py-0' : 'px-3 py-3',
        )}
      >
        <button
          type="button"
          disabled={busy || speaking || wsStatus !== 'open'}
          onClick={() => void toggleMic()}
          className={cn(
            'relative shrink-0 overflow-hidden rounded-full transition',
            isHeader ? 'h-10 w-10' : 'h-16 w-16',
            (busy || speaking || wsStatus !== 'open') &&
              'cursor-not-allowed opacity-70',
            recording && 'ring-2 ring-danger/60',
          )}
          aria-label={actionLabel}
        >
          <AgentAudioVisualizerAura
            size="sm"
            state={agentState}
            color={pendingMode === 'hitl' || pendingMode === 'ambient' ? '#FBBF24' : '#22C55E'}
            colorShift={0.2}
            themeMode={isHeader ? 'light' : 'dark'}
            className="h-full w-full"
          />
        </button>

        <div className="min-w-0 flex-1">
          <div className="mb-0.5 flex items-center gap-2">
            <p
              className={cn(
                'text-[10px] font-semibold tracking-[0.12em]',
                isHeader ? 'text-[#1E4D38]' : 'text-emerald-300',
              )}
            >
              {VOICE_AGENT_STATE_LABEL[agentState] || agentState.toUpperCase()}
            </p>
            <span
              className={cn(
                'rounded-full px-1.5 py-0.5 text-[9px]',
                wsStatus === 'open'
                  ? isHeader
                    ? 'bg-[#E8F5EB] text-[#2E7D32]'
                    : 'bg-emerald-400/10 text-emerald-300'
                  : isHeader
                    ? 'bg-[#F0F4EE] text-[#88968E]'
                    : 'bg-white/5 text-white/45',
              )}
            >
              WS {wsStatus}
            </span>
          </div>
          <p
            className={cn(
              'truncate text-xs',
              isHeader ? 'text-[#5A6860]' : 'text-text-secondary',
            )}
          >
            {actionLabel}
          </p>
          {busy ? (
            <p
              className={cn(
                'mt-0.5 text-[11px]',
                isHeader ? 'text-[#1E4D38]' : 'text-emerald-200/80',
              )}
            >
              Đang xử lý…
            </p>
          ) : last ? (
            <div
              className={cn(
                'mt-0.5 space-y-0.5 text-[11px] leading-snug',
                isHeader
                  ? 'max-h-24 overflow-x-hidden overflow-y-auto pr-1'
                  : 'max-h-20 overflow-y-auto',
              )}
            >
              {last.transcript !== undefined ? (
                <p
                  className={cn(
                    'truncate',
                    isHeader ? 'text-[#88968E]' : 'text-text-muted',
                  )}
                  title={last.transcript}
                >
                  Bạn:{' '}
                  <span className={isHeader ? 'text-[#5A6860]' : 'text-text-secondary'}>
                    {last.transcript || '—'}
                  </span>
                </p>
              ) : null}
              <p
                className={cn(
                  'whitespace-pre-wrap break-words',
                  isHeader ? 'text-[#1C2721]' : 'text-text-primary',
                )}
                title={last.response}
              >
                Agent: {last.response}
              </p>
            </div>
          ) : (
            <p
              className={cn(
                'mt-0.5 truncate text-[11px]',
                isHeader ? 'text-[#88968E]' : 'text-text-muted',
              )}
            >
              Nói lệnh — vd. «Bật đèn phòng khách»
            </p>
          )}
          {recording ? (
            <p className="mt-0.5 animate-pulse text-[11px] text-danger">
              ● REC — nhấn lại để gửi
            </p>
          ) : null}
          {micError ? (
            <p className="mt-0.5 text-[11px] text-danger">{micError}</p>
          ) : null}
        </div>

        <div className="flex shrink-0 flex-col items-end gap-1">
          <Button
            variant={traceOpen ? 'outline' : 'ghost'}
            size="xs"
            aria-expanded={traceOpen}
            aria-label={traceOpen ? 'Đóng agent trace' : 'Mở agent trace'}
            title="Agent trace"
            onClick={() => setTraceOpen((open) => !open)}
          >
            Trace
            {traceEvents.length > 0 ? (
              <span className="ml-1 rounded-full bg-[#1E4D38]/15 px-1.5 text-[9px] text-[#1E4D38]">
                {traceEvents.length}
              </span>
            ) : null}
          </Button>
          {recording ? (
            <Button
              variant="ghost"
              size="xs"
              disabled={busy}
              onClick={() => cancel()}
            >
              Huỷ
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  )
}
