import { useCallback, useEffect, useRef, useState } from "react";
import { voiceWsUrl } from "@/config/api";
import { AI_ENABLED } from '@/config/features'

export type VoiceAckPayload = {
  text?: string;
  reply?: string;
  intent?: string;
  actions?: unknown[];
  needs_clarify?: boolean;
  needs_hitl?: boolean;
  clarify_question?: string;
  hitl_request_id?: string;
  hitl_action_summary?: string;
};

export type VoiceSessionResult = VoiceAckPayload & {
  session_id: string;
  audio_format?: string;
  audio_base64?: string;
};

type WsStatus = "idle" | "connecting" | "open" | "closed" | "error";

type WsEnvelope = {
  type: string;
  session_id?: string;
  payload?: VoiceAckPayload & {
    audio_format?: string;
    audio_base64?: string;
  };
};

const RESPONSE_TIMEOUT_MS = 120_000;

export function useVoiceSession() {
  const wsRef = useRef<WebSocket | null>(null)
  const sessionIdRef = useRef<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const pendingRef = useRef<{
    resolve: (value: VoiceSessionResult) => void;
    reject: (reason: Error) => void;
    ack: WsEnvelope | null;
  } | null>(null);
  const [status, setStatus] = useState<WsStatus>("idle");

  const settlePending = useCallback((result: VoiceSessionResult) => {
    pendingRef.current?.resolve(result);
    pendingRef.current = null;
  }, []);

  const failPending = useCallback((message: string) => {
    pendingRef.current?.reject(new Error(message));
    pendingRef.current = null;
  }, []);

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      let msg: WsEnvelope;
      try {
        msg = JSON.parse(event.data as string) as WsEnvelope;
      } catch {
        return;
      }

      if (msg.type === 'session' && msg.session_id) {
        sessionIdRef.current = msg.session_id
        setSessionId(msg.session_id)
        return
      }

      if (msg.type === "ack") {
        if (!pendingRef.current) return;
        pendingRef.current.ack = msg;
        return;
      }

      if (msg.type === "audio" && pendingRef.current?.ack) {
        const ack = pendingRef.current.ack;
        const payload = ack.payload || {};
        const audioPayload = msg.payload || {};
        settlePending({
          session_id: ack.session_id || sessionIdRef.current || "",
          text: payload.text,
          reply: payload.reply,
          intent: payload.intent,
          actions: payload.actions,
          needs_clarify: payload.needs_clarify,
          needs_hitl: payload.needs_hitl,
          clarify_question: payload.clarify_question,
          hitl_request_id: payload.hitl_request_id,
          hitl_action_summary: payload.hitl_action_summary,
          audio_format: audioPayload.audio_format,
          audio_base64: audioPayload.audio_base64,
        });
      }
    },
    [settlePending],
  );

  const connect = useCallback(() => {
    if (!AI_ENABLED) return Promise.reject(new Error('AI sẽ được tích hợp ở giai đoạn tiếp theo.'))
    if (wsRef.current?.readyState === WebSocket.OPEN) return Promise.resolve();
    if (wsRef.current?.readyState === WebSocket.CONNECTING) {
      return new Promise<void>((resolve, reject) => {
        const ws = wsRef.current;
        if (!ws) {
          reject(new Error("WebSocket không khả dụng"));
          return;
        }
        ws.addEventListener("open", () => resolve(), { once: true });
        ws.addEventListener(
          "error",
          () => reject(new Error("Không kết nối được voice WebSocket")),
          {
            once: true,
          },
        );
      });
    }

    return new Promise<void>((resolve, reject) => {
      setStatus("connecting");
      const ws = new WebSocket(voiceWsUrl());
      wsRef.current = ws;
      ws.onopen = () => {
        setStatus("open");
        resolve();
      };
      ws.onerror = () => {
        setStatus("error");
        reject(new Error("Không kết nối được voice WebSocket"));
      };
      ws.onclose = () => {
        setStatus('closed')
        sessionIdRef.current = null
        setSessionId(null)
        wsRef.current = null
        failPending('Voice WebSocket đã đóng')
      }
      ws.onmessage = handleMessage
    })
  }, [failPending, handleMessage])

  const sendAudio = useCallback(
    async (wavBytes: Uint8Array): Promise<VoiceSessionResult> => {
      await connect();
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        throw new Error("Voice WebSocket chưa sẵn sàng");
      }

      return new Promise<VoiceSessionResult>((resolve, reject) => {
        const timer = window.setTimeout(() => {
          pendingRef.current = null;
          reject(new Error("Hết thời gian chờ phản hồi giọng nói"));
        }, RESPONSE_TIMEOUT_MS);

        pendingRef.current = {
          resolve: (value) => {
            window.clearTimeout(timer);
            resolve(value);
          },
          reject: (reason) => {
            window.clearTimeout(timer);
            reject(reason);
          },
          ack: null,
        };

        const buffer = wavBytes.buffer.slice(
          wavBytes.byteOffset,
          wavBytes.byteOffset + wavBytes.byteLength,
        ) as ArrayBuffer;
        ws.send(buffer);
      });
    },
    [connect],
  );

  const sendJson = useCallback(
    async (payload: Record<string, unknown>) => {
      await connect();
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        throw new Error("Voice WebSocket chưa sẵn sàng");
      }
      ws.send(JSON.stringify(payload));
    },
    [connect],
  );

  useEffect(() => {
    let cancelled = false;
    let retryTimer: number | undefined;

    const open = () => {
      void connect().catch(() => {
        if (cancelled) return;
        retryTimer = window.setTimeout(open, 1500);
      });
    };
    open();

    return () => {
      cancelled = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      failPending("Voice session đã đóng");
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect, failPending]);

  useEffect(() => {
    if (status !== "closed") return;
    const timer = window.setTimeout(() => {
      void connect().catch(() => {
        /* badge shows closed/error until next success */
      })
    }, 1200)
    return () => window.clearTimeout(timer)
  }, [status, connect])

  return { status, sessionId, connect, sendAudio, sendJson }
}
