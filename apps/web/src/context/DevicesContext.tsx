import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { applyDeviceAction, fetchDevices } from "@/api/devices";
import { getAccessToken } from "@/api/http";
import { respondAmbientSuggestion as sendAmbientSuggestionDecision } from "@/api/ambient";
import { devicesWsUrl } from "@/config/api";
import { useSession } from "@/context/SessionContext";
import { useToast } from "@/context/ToastContext";
import type { Device, DeviceState, DeviceStateValue } from "@/types/device";
import type { AmbientSuggestion } from "@/types/ambient";
import { playBase64Audio } from "@/utils/audioWav";

type WsSnapshotMessage = {
  type: "snapshot";
  devices: Device[];
  ts: string;
};

type WsDeviceUpdatedMessage = {
  type: "device.updated";
  device_id: string;
  state: DeviceState;
  ts: string;
};

type WsScheduleExecutedMessage = {
  type: "schedule.executed";
  schedule_id: string;
  schedule_name: string;
  status: "success" | "failed";
  error_message?: string | null;
};

type WsMessage = WsSnapshotMessage | WsDeviceUpdatedMessage | WsScheduleExecutedMessage | AmbientSuggestion;

type DevicesContextValue = {
  devices: Device[];
  loading: boolean;
  error: string | null;
  connected: boolean;
  refresh: () => Promise<void>;
  applyAction: (
    deviceId: string,
    key: string,
    value?: DeviceStateValue | null,
  ) => Promise<Device | null>;
  ambientSuggestions: AmbientSuggestion[];
  dismissAmbientSuggestion: (requestId: string) => void;
  respondAmbientSuggestion: (requestId: string, approved: boolean) => Promise<void>;
};

const DevicesContext = createContext<DevicesContextValue | null>(null);

function mergeDeviceState(
  devices: Device[],
  deviceId: string,
  state: DeviceState,
): Device[] {
  return devices.map((d) =>
    d.id === deviceId ? { ...d, state: { ...state } } : d,
  );
}

function upsertDevice(devices: Device[], device: Device): Device[] {
  const exists = devices.some((d) => d.id === device.id);
  if (!exists) return [...devices, device];
  return devices.map((d) => (d.id === device.id ? device : d));
}

/** Cleanup socket without Chrome warning under React StrictMode. */
function abandonSocket(ws: WebSocket | null) {
  if (!ws) return;
  ws.onopen = null;
  ws.onclose = null;
  ws.onerror = null;
  ws.onmessage = null;
  // Chỉ close khi đã OPEN. Close lúc CONNECTING → warning
  // "WebSocket is closed before the connection is established".
  if (ws.readyState === WebSocket.OPEN) {
    try {
      ws.close();
    } catch {
      // ignore
    }
  }
}

export function DevicesProvider({ children }: { children: ReactNode }) {
  const { showToast } = useToast();
  const { session, authReady } = useSession();
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [ambientSuggestions, setAmbientSuggestions] = useState<AmbientSuggestion[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<number | null>(null);

  const dismissAmbientSuggestion = useCallback((requestId: string) => {
    setAmbientSuggestions((prev) => prev.filter((s) => s.request_id !== requestId));
  }, []);

  const respondAmbientSuggestion = useCallback(
    async (requestId: string, approved: boolean) => {
      try {
        const result = await sendAmbientSuggestionDecision(requestId, approved);
        dismissAmbientSuggestion(requestId);
        showToast(
          approved
            ? result.executed
              ? `Đã tắt ${result.device_ids.length} thiết bị.`
              : "Không còn thiết bị phù hợp để tắt."
            : "Đã giữ nguyên các thiết bị.",
          approved && result.executed ? "success" : "info",
        );
      } catch (err) {
        dismissAmbientSuggestion(requestId);
        showToast(
          err instanceof Error ? err.message : "Không xử lý được xác nhận.",
          "error",
        );
      }
    },
    [dismissAmbientSuggestion, showToast],
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDevices();
      setDevices(data);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Không tải được thiết bị";
      setError(message);
      showToast(message, "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  const applyAction = useCallback(
    async (deviceId: string, key: string, value?: DeviceStateValue | null) => {
      try {
        const result = await applyDeviceAction(deviceId, key, value);
        setDevices((prev) => upsertDevice(prev, result.device));
        return result.device;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Điều khiển thất bại";
        showToast(message, "error");
        return null;
      }
    },
    [showToast],
  );

  useEffect(() => {
    if (!authReady || !session) {
      setDevices([]);
      setLoading(false);
      return;
    }
    void refresh();
  }, [authReady, session, refresh]);

  useEffect(() => {
    if (!authReady || !session) {
      return;
    }
    let cancelled = false;

    const clearReconnect = () => {
      if (reconnectTimer.current !== null) {
        window.clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
    };

    const connect = () => {
      if (cancelled) return;
      clearReconnect();
      abandonSocket(wsRef.current);
      wsRef.current = null;

      const socketUrl = new URL(devicesWsUrl());
      socketUrl.searchParams.set('token', getAccessToken());
      const ws = new WebSocket(socketUrl.toString());
      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelled || wsRef.current !== ws) return;
        setConnected(true);
      };

      ws.onclose = () => {
        if (wsRef.current === ws) wsRef.current = null;
        if (cancelled) return;
        setConnected(false);
        reconnectTimer.current = window.setTimeout(connect, 2000);
      };

      ws.onerror = () => {
        // onclose handles reconnect
      };

      ws.onmessage = (event) => {
        if (cancelled || wsRef.current !== ws) return;
        try {
          const message = JSON.parse(event.data as string) as WsMessage;
          if (message.type === "snapshot") {
            setDevices(message.devices);
            setLoading(false);
            setError(null);
            return;
          }
          if (message.type === "device.updated") {
            setDevices((prev) =>
              mergeDeviceState(prev, message.device_id, message.state),
            );
            return;
          }
          if (message.type === "schedule.executed") {
            showToast(
              message.status === "success"
                ? `Đã chạy lịch ${message.schedule_name}`
                : `Lịch ${message.schedule_name} thất bại${message.error_message ? `: ${message.error_message}` : ""}`,
              message.status === "success" ? "success" : "error",
            );
            window.dispatchEvent(new CustomEvent("schedule.executed", { detail: message }));
            return;
          }
          if (message.type === "ambient.suggestion") {
            setAmbientSuggestions((prev) => [
              ...prev.filter((s) => s.request_id !== message.request_id),
              message,
            ]);
            window.setTimeout(() => {
              setAmbientSuggestions((prev) =>
                prev.filter((s) => s.request_id !== message.request_id),
              );
            }, message.expires_in_seconds * 1000);
            window.dispatchEvent(
              new CustomEvent("ambient.suggestion", { detail: message }),
            );
            if (message.audio_base64) {
              void playBase64Audio(message.audio_format, message.audio_base64).catch(() => {
                showToast("Trình duyệt đang chặn phát giọng nói tự động.", "error");
              });
            }
          }
        } catch {
          // ignore
        }
      };
    };

    // Defer past React StrictMode mount→unmount→remount so socket
    // is only created on the "real" mount.
    const startTimer = window.setTimeout(connect, 50);

    return () => {
      cancelled = true;
      window.clearTimeout(startTimer);
      clearReconnect();
      abandonSocket(wsRef.current);
      wsRef.current = null;
    };
  }, [authReady, session, showToast]);

  const value = useMemo(
    () => ({
      devices,
      loading,
      error,
      connected,
      refresh,
      applyAction,
      ambientSuggestions,
      dismissAmbientSuggestion,
      respondAmbientSuggestion,
    }),
    [
      devices,
      loading,
      error,
      connected,
      refresh,
      applyAction,
      ambientSuggestions,
      dismissAmbientSuggestion,
      respondAmbientSuggestion,
    ],
  );

  return (
    <DevicesContext.Provider value={value}>{children}</DevicesContext.Provider>
  );
}

export function useDevices(): DevicesContextValue {
  const ctx = useContext(DevicesContext);
  if (!ctx) {
    throw new Error("useDevices must be used within DevicesProvider");
  }
  return ctx;
}
