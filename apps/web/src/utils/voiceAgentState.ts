import type { AgentState } from '@livekit/components-react'

type WsStatus = 'idle' | 'connecting' | 'open' | 'closed' | 'error'

export const VOICE_AGENT_STATE_LABEL: Record<string, string> = {
  connecting: 'CONNECTING',
  listening: 'LISTENING',
  thinking: 'THINKING',
  speaking: 'SPEAKING',
  disconnected: 'DISCONNECTED',
  failed: 'FAILED',
}

export function deriveVoiceAgentState(
  wsStatus: WsStatus,
  recording: boolean,
  busy: boolean,
  speaking: boolean,
): AgentState {
  if (wsStatus === 'connecting' || wsStatus === 'idle') return 'connecting'
  if (wsStatus === 'error') return 'failed'
  if (wsStatus === 'closed') return 'disconnected'
  if (speaking) return 'speaking'
  if (busy) return 'thinking'
  if (recording) return 'listening'
  return 'listening'
}
