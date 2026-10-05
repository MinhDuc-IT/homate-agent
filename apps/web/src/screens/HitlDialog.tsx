import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AlertTriangleIcon } from "@/assets/icons/HomeMindIcons";
import { OverlayPanel } from "@/components/homemind/OverlayPanel";
import { Button } from "@/components/ui/Button";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { API_HITL } from "@/config/api";
import { apiFetch } from "@/api/http";
import { ROUTES } from "@/config/routes";
import { useDevices } from "@/context/DevicesContext";
import { useSession } from "@/context/SessionContext";
import { useToast } from "@/context/ToastContext";
import type { HitlNavState } from "@/types/voice";

const HITL_TIMEOUT_SECONDS = 30;

type ConfirmResult = {
  request_id: string;
  session_id: string;
  approved: boolean;
  action_summary: string;
  executed?: boolean;
  message?: string;
};

export function HitlDialog() {
  const navigate = useNavigate();
  const location = useLocation();
  const { session } = useSession();
  const { showToast } = useToast();
  const { refresh } = useDevices();
  const [busy, setBusy] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(HITL_TIMEOUT_SECONDS);
  const confirmingRef = useRef(false);
  const timerRef = useRef<number | null>(null);
  const requester = session?.memberName ?? "Đức";

  const nav = (location.state as HitlNavState | null) || null;
  const requestId = nav?.requestId || "";
  const actionSummary = nav?.actionSummary || "Hành động nhạy cảm cần xác nhận";

  function stopTimer() {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  async function confirm(
    approved: boolean,
    reason: "user" | "timeout" = "user",
  ) {
    if (confirmingRef.current) return;
    if (!requestId) {
      showToast("Thiếu request_id — hãy gửi lại lệnh từ Demo Voice", "error");
      navigate(ROUTES.voice, { replace: true });
      return;
    }
    confirmingRef.current = true;
    stopTimer();
    setBusy(true);
    try {
      const res = await apiFetch(`${API_HITL}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: requestId, approved }),
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      const data = (await res.json()) as ConfirmResult;
      window.setTimeout(() => {
        void refresh();
      }, 400);
      if (approved) {
        showToast(
          data.message || data.action_summary || "Đã xác nhận",
          "success",
        );
      } else if (reason === "timeout") {
        showToast("Hết thời gian xác nhận — đã hủy yêu cầu", "warning");
      } else {
        showToast(data.message || "Đã hủy yêu cầu", "info");
      }
      navigate(ROUTES.voice, { replace: true });
    } catch (err) {
      confirmingRef.current = false;
      const msg = err instanceof Error ? err.message : "HITL lỗi";
      showToast(msg, "error");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!requestId) return;
    confirmingRef.current = false;
    setSecondsLeft(HITL_TIMEOUT_SECONDS);
    stopTimer();
    const started = Date.now();
    timerRef.current = window.setInterval(() => {
      if (confirmingRef.current) return;
      const elapsed = Math.floor((Date.now() - started) / 1000);
      const left = Math.max(HITL_TIMEOUT_SECONDS - elapsed, 0);
      setSecondsLeft(left);
      if (left <= 0) {
        stopTimer();
        void confirm(false, "timeout");
      }
    }, 250);
    return () => stopTimer();
    // Restart countdown when a new HITL request opens
    // eslint-disable-next-line react-hooks/exhaustive-deps -- confirm reads latest requestId via closure reset on requestId
  }, [requestId]);

  const progressPercent = (secondsLeft / HITL_TIMEOUT_SECONDS) * 100;

  return (
    <div>
      <OverlayPanel>
        <p className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-warning">
          <AlertTriangleIcon className="h-4 w-4" />
          Cần xác nhận
        </p>
        <p className="mb-1 text-[15px] font-medium text-text-primary">
          {actionSummary}?
        </p>
        <p className="mb-3.5 text-sm text-text-secondary">
          Yêu cầu bởi {requester}
          {requestId ? (
            <span className="text-text-muted">
              {" "}
              · id {requestId.slice(0, 8)}…
            </span>
          ) : null}
          {requestId ? (
            <span className="font-medium text-warning">
              {" "}
              · {busy ? "Đang xử lý…" : `Hết hạn sau ${secondsLeft}s`}
            </span>
          ) : null}
        </p>
        <ProgressBar
          value={progressPercent}
          color="error"
          className="mb-3.5"
          showLabel
          label={busy ? "…" : `${secondsLeft}s`}
        />

        {!requestId ? (
          <p className="mb-3 text-xs text-danger">
            Không có HITL request. Hãy gửi «Mở khóa cửa chính» từ Voice Panel.
          </p>
        ) : null}

        <div className="flex gap-2">
          <Button
            variant="outline"
            className="flex-1"
            disabled={busy || !requestId}
            onClick={() => void confirm(false)}
          >
            Hủy
          </Button>
          <Button
            variant="danger"
            className="flex-1"
            disabled={busy || !requestId}
            onClick={() => void confirm(true)}
          >
            {busy ? "Đang xử lý…" : "Đồng ý"}
          </Button>
        </div>
      </OverlayPanel>
    </div>
  );
}
