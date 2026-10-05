/** Backend API / WebSocket base URLs for HomeMind Hub frontend. */

/** Empty string = same origin (Vite proxy to FastAPI in dev). */
export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

/** Contract path — Visual UI dashboard REST */
export const API_DASHBOARD = `${API_BASE_URL}/api/dashboard`;

/** HITL confirm REST */
export const API_HITL = `${API_BASE_URL}/api/hitl`;

/** @deprecated Prefer API_DASHBOARD — kept for gradual migration */
export const API_V1 = `${API_BASE_URL}/api/v1`;

function wsBaseUrl(path: string): string {
  const envKey = path === "/ws/voice" ? "VITE_VOICE_WS_URL" : "VITE_WS_URL";
  const explicit = import.meta.env[envKey] as string | undefined;
  if (explicit) return explicit;

  if (API_BASE_URL) {
    const base = new URL(API_BASE_URL);
    const wsProtocol = base.protocol === "https:" ? "wss:" : "ws:";
    return `${wsProtocol}//${base.host}${path}`;
  }

  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${wsProtocol}//${window.location.host}${path}`;
}

export function devicesWsUrl(): string {
  return wsBaseUrl("/ws/devices");
}

export function voiceWsUrl(): string {
  return wsBaseUrl("/ws/voice");
}

export function agentTraceWsUrl(sessionId: string): string {
  const explicit = import.meta.env.VITE_AGENT_TRACE_WS_URL as string | undefined
  if (explicit) return `${explicit.replace(/\/$/, '')}/${encodeURIComponent(sessionId)}`
  const deviceSocket = import.meta.env.VITE_WS_URL as string | undefined
  if (deviceSocket) {
    const base = new URL(deviceSocket)
    return `${base.protocol}//${base.host}/ws/agent-trace/${encodeURIComponent(sessionId)}`
  }
  return `${wsBaseUrl('/ws/agent-trace')}/${encodeURIComponent(sessionId)}`
}
