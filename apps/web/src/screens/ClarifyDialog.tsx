import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { HelpCircleIcon } from "@/assets/icons/HomeMindIcons";
import { OverlayPanel } from "@/components/homemind/OverlayPanel";
import { AgentTracePanel } from "@/components/homemind/AgentTracePanel";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { API_DASHBOARD } from "@/config/api";
import { apiFetch } from "@/api/http";
import { ROUTES } from "@/config/routes";
import { useDevices } from "@/context/DevicesContext";
import { useAgentTrace } from "@/hooks/useAgentTrace";
import { useToast } from "@/context/ToastContext";
import type { ClarifyNavState, HitlNavState } from "@/types/voice";

const ROOM_OPTIONS = ["Phòng khách", "Phòng ngủ", "Bếp"];
const ACTION_OPTIONS = ["Bật", "Tắt"];

type ChatResult = {
  response: string;
  needs_clarify?: boolean;
  needs_hitl?: boolean;
  session_id?: string;
  clarify_question?: string;
  hitl_request_id?: string;
  hitl_action_summary?: string;
  actions?: unknown[];
};

export function ClarifyDialog() {
  const navigate = useNavigate();
  const location = useLocation();
  const { showToast } = useToast();
  const { refresh } = useDevices();
  const [busy, setBusy] = useState(false);
  const [freeText, setFreeText] = useState("");

  const nav = (location.state as ClarifyNavState | null) || null;
  const question = nav?.question || "Cần làm rõ thêm về lệnh của bạn.";
  const sessionId = nav?.sessionId || "";
  const originalMessage = nav?.originalMessage || "";
  const { events: traceEvents, status: traceStatus, clear: clearTrace } =
    useAgentTrace(sessionId || null);

  const quickOptions = useMemo(() => {
    const q = question.toLowerCase();
    if (q.includes("bật") || q.includes("tắt") || q.includes("độ sáng")) {
      return ACTION_OPTIONS;
    }
    if (q.includes("phòng") || q.includes("ở đâu")) {
      return ROOM_OPTIONS;
    }
    return [...ACTION_OPTIONS, ...ROOM_OPTIONS];
  }, [question]);

  async function submitAnswer(answer: string) {
    if (!sessionId) {
      showToast("Thiếu session — hãy gửi lại lệnh từ Voice Panel", "error");
      navigate(ROUTES.voice, { replace: true });
      return;
    }
    setBusy(true);
    clearTrace();
    try {
      const res = await apiFetch(`${API_DASHBOARD}/clarify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, answer }),
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      const data = (await res.json()) as ChatResult;
      window.setTimeout(() => {
        void refresh();
      }, 600);

      if (data.needs_clarify) {
        showToast(data.response, "warning");
        navigate(ROUTES.clarify, {
          replace: true,
          state: {
            sessionId: data.session_id || sessionId,
            question: data.clarify_question || data.response,
            originalMessage,
          } satisfies ClarifyNavState,
        });
        return;
      }
      if (data.needs_hitl) {
        showToast(data.response, "warning");
        navigate(ROUTES.hitl, {
          replace: true,
          state: {
            sessionId: data.session_id || sessionId,
            requestId: data.hitl_request_id || "",
            actionSummary: data.hitl_action_summary || data.response,
          } satisfies HitlNavState,
        });
        return;
      }
      showToast(data.response || "Đã xử lý sau khi làm rõ", "success");
      navigate(ROUTES.voice, { replace: true });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Clarify lỗi";
      showToast(msg, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <OverlayPanel>
        <p className="mb-1.5 flex items-center gap-1.5 text-sm text-text-secondary">
          <HelpCircleIcon className="h-4 w-4" />
          Cần làm rõ
        </p>
        {originalMessage ? (
          <p className="mb-2 text-xs text-text-muted">
            Lệnh gốc: {originalMessage}
          </p>
        ) : null}
        <p className="mb-3.5 text-[15px] font-medium text-text-primary">
          {question}
        </p>

        <div className="mb-3 flex flex-wrap gap-2">
          {quickOptions.map((option) => (
            <Button
              key={option}
              variant="outline"
              size="sm"
              disabled={busy || !sessionId}
              onClick={() => void submitAnswer(option)}
            >
              {option}
            </Button>
          ))}
        </div>

        <div className="mb-3 flex flex-col gap-2 sm:flex-row">
          <Input
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
            placeholder="Hoặc gõ câu trả lời…"
            className="flex-1"
            disabled={busy}
          />
          <Button
            disabled={busy || !freeText.trim() || !sessionId}
            onClick={() => void submitAnswer(freeText.trim())}
          >
            {busy ? "Đang gửi…" : "Gửi"}
          </Button>
        </div>

        {!sessionId ? (
          <p className="mb-3 text-xs text-danger">
            Không có session clarify. Hãy quay lại Demo Voice và gửi lệnh mơ hồ
            (vd. “Đèn phòng khách”).
          </p>
        ) : null}

        <Button
          variant="ghost"
          size="sm"
          disabled={busy}
          onClick={() => navigate(ROUTES.voice)}
        >
          Hủy
        </Button>
        <div className="mt-4">
          <AgentTracePanel events={traceEvents} status={traceStatus} />
        </div>
      </OverlayPanel>
    </div>
  );
}
