import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckIcon, MicIcon } from '@/assets/icons/HomeMindIcons'
import { BackButton } from '@/components/ui/BackButton'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { apiFetch } from '@/api/http'
import { API_DASHBOARD } from '@/config/api'
import { ROUTES } from '@/config/routes'
import { useDevices } from '@/context/DevicesContext'
import { useToast } from '@/context/ToastContext'
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder'
import { useVoiceSession } from '@/hooks/useVoiceSession'
import { useAgentTrace } from '@/hooks/useAgentTrace'
import { AgentTracePanel } from '@/components/homemind/AgentTracePanel'
import type { ClarifyNavState, HitlNavState } from '@/types/voice'
import { playBase64Audio } from '@/utils/audioWav'
import { cn } from '@/utils/cn'

export type { ClarifyNavState, HitlNavState } from "@/types/voice";

const SUGGESTIONS = [
  "Đèn phòng khách",
  "Bật đèn phòng khách",
  "Tắt đèn phòng khách",
  "Đặt độ sáng đèn phòng khách 40%",
  "Bật điều hòa phòng khách",
  "Bật đèn phòng khách và kéo rèm phòng khách",
  "Mở khóa cửa chính",
  "Đóng khóa cửa chính",
];

type ChatResult = {
  response: string;
  transcript?: string;
  intent?: string;
  actions?: unknown[];
  needs_clarify?: boolean;
  needs_hitl?: boolean;
  session_id?: string;
  clarify_question?: string;
  hitl_request_id?: string;
  hitl_action_summary?: string;
};

const WS_STATUS_LABEL: Record<string, string> = {
  idle: "Chưa kết nối",
  connecting: "Đang kết nối…",
  open: "Sẵn sàng",
  closed: "Đã ngắt",
  error: "Lỗi kết nối",
};

export function VoicePanel() {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const { refresh } = useDevices()
  const { recording, error: micError, start, stop, cancel } = useVoiceRecorder()
  const { status: wsStatus, sendAudio } = useVoiceSession()
  const [textSessionId] = useState(() => crypto.randomUUID())
  const [traceSessionId, setTraceSessionId] = useState<string | null>(textSessionId)
  const { events: traceEvents, status: traceStatus, clear: clearTrace } = useAgentTrace(traceSessionId)
  const [text, setText] = useState('Đèn phòng khách')
  const [busy, setBusy] = useState(false)
  const [last, setLast] = useState<ChatResult | null>(null)

  const handleResult = useCallback(
    (data: ChatResult, originalMessage: string) => {
      setLast(data);
      window.setTimeout(() => {
        void refresh();
      }, 600);

      if (data.needs_hitl) {
        showToast(data.response, "warning");
        const state: HitlNavState = {
          sessionId: data.session_id || "",
          requestId: data.hitl_request_id || "",
          actionSummary: data.hitl_action_summary || data.response,
        };
        navigate(ROUTES.hitl, { state });
        return;
      }
      if (data.needs_clarify) {
        showToast(data.response, "warning");
        const state: ClarifyNavState = {
          sessionId: data.session_id || "",
          question: data.clarify_question || data.response,
          originalMessage,
        };
        navigate(ROUTES.clarify, { state });
        return;
      }
      showToast(data.response || "Đã xử lý", "success");
    },
    [navigate, refresh, showToast],
  );

  async function runTextPipeline(message: string) {
    setBusy(true)
    setTraceSessionId(textSessionId)
    clearTrace()
    try {
      const res = await apiFetch(`${API_DASHBOARD}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: textSessionId }),
      })
      if (!res.ok) {
        throw new Error(await res.text());
      }
      const data = (await res.json()) as ChatResult;
      handleResult({ ...data, transcript: message }, message);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Pipeline lỗi";
      showToast(msg, "error");
    } finally {
      setBusy(false);
    }
  }

  async function runVoicePipeline(wavBytes: Uint8Array) {
    setBusy(true);
    try {
      const data = await sendAudio(wavBytes)
      if (data.session_id) setTraceSessionId(data.session_id)
      const transcript = (data.text || '').trim()
      handleResult(
        {
          response: data.reply || "",
          transcript,
          intent: data.intent,
          actions: data.actions,
          needs_clarify: data.needs_clarify,
          needs_hitl: data.needs_hitl,
          session_id: data.session_id,
          clarify_question: data.clarify_question,
          hitl_request_id: data.hitl_request_id,
          hitl_action_summary: data.hitl_action_summary,
        },
        transcript,
      );
      if (data.audio_base64) {
        void playBase64Audio(data.audio_format, data.audio_base64);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Voice pipeline lỗi";
      showToast(msg, "error");
    } finally {
      setBusy(false);
    }
  }

  async function toggleMic() {
    if (busy) return;

    if (wsStatus !== "open") {
      showToast(
        "Voice WebSocket chưa sẵn sàng — kiểm tra backend :8000",
        "error",
      );
      return;
    }

    if (recording) {
      const wav = await stop();
      if (!wav || wav.length === 0) {
        showToast(
          "Không ghi được audio — nói lâu hơn 1 giây rồi nhấn lại",
          "warning",
        );
        return;
      }
      await runVoicePipeline(wav);
      return;
    }

    const ok = await start();
    if (ok) {
      showToast("Đang nghe… nhấn mic lần nữa để gửi", "info");
    } else {
      showToast(micError || "Không mở được micro", "error");
    }
  }

  const micLabel = recording
    ? "Nhấn để dừng và gửi"
    : busy
      ? "Đang xử lý…"
      : "Nhấn để nói";

  return (
    <div>
      <BackButton label="Về nhà" onClick={() => navigate(ROUTES.dashboard)} />
      <Card>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <p className="flex items-center gap-1.5 text-sm font-medium text-homemind">
            <MicIcon className="h-4 w-4" />
            Demo pipeline (text / mic → Agent)
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(ROUTES.voiceAgent)}
            >
              Voice Agent
            </Button>
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs",
                wsStatus === "open"
                  ? "bg-emerald-400/10 text-emerald-300"
                  : wsStatus === "connecting"
                    ? "bg-amber-400/10 text-amber-300"
                    : "bg-white/5 text-text-muted",
              )}
            >
              WS: {WS_STATUS_LABEL[wsStatus] || wsStatus}
            </span>
          </div>
        </div>

        <div className="mb-5 flex flex-col items-center gap-3 rounded-xl border border-dashed border-sidebar-border bg-homemind-subtle/40 px-4 py-6">
          <button
            type="button"
            disabled={busy}
            onClick={() => void toggleMic()}
            className={cn(
              "flex h-20 w-20 items-center justify-center rounded-full border-2 shadow-sm transition",
              recording
                ? "animate-pulse border-danger bg-danger-light text-danger"
                : "border-homemind/30 bg-elevated text-homemind hover:border-homemind hover:bg-homemind-subtle",
              busy && "cursor-not-allowed opacity-60",
            )}
            aria-label={micLabel}
          >
            <MicIcon className="h-9 w-9" />
          </button>
          <p className="text-sm font-medium text-text-primary">{micLabel}</p>
          {recording ? (
            <Button
              variant="ghost"
              size="sm"
              disabled={busy}
              onClick={() => cancel()}
            >
              Huỷ ghi âm
            </Button>
          ) : null}
          {micError ? <p className="text-xs text-danger">{micError}</p> : null}
        </div>

        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-text-muted">
          Hoặc nhập text (REST)
        </p>

        <div className="mb-3 flex flex-col gap-2 sm:flex-row">
          <Input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Nhập lệnh tiếng Việt…"
            className="flex-1"
            disabled={busy || recording}
          />
          <Button
            disabled={busy || recording || !text.trim()}
            onClick={() => void runTextPipeline(text.trim())}
          >
            {busy && !recording ? "Đang xử lý…" : "Gửi lệnh"}
          </Button>
        </div>

        <div className="mb-4 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <Button
              key={s}
              variant="outline"
              size="sm"
              disabled={busy || recording}
              onClick={() => {
                setText(s);
                void runTextPipeline(s);
              }}
            >
              {s}
            </Button>
          ))}
        </div>

        {last && (
          <div className="border-t border-sidebar-border pt-3">
            {last.transcript !== undefined ? (
              <p className="mb-2 text-sm text-text-secondary">
                Transcript:{" "}
                <span className="text-text-primary">
                  {last.transcript || "—"}
                </span>
              </p>
            ) : null}
            <p className="mb-2 text-sm text-text-secondary">
              Intent:{" "}
              <span className="text-text-primary">{last.intent || "—"}</span>
            </p>
            <p className="mb-2 flex items-start gap-2 text-sm text-text-primary">
              <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-success" />
              {last.response}
            </p>
            {!!last.actions?.length && (
              <pre className="overflow-x-auto rounded bg-white/5 p-2 text-xs">
                {JSON.stringify(last.actions, null, 2)}
              </pre>
            )}
          </div>
        )}
        <div className="mt-4">
          <AgentTracePanel events={traceEvents} status={traceStatus} />
        </div>
      </Card>
    </div>
  );
}
