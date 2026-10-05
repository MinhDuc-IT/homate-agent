import { useCallback, useEffect, useRef, useState } from 'react'
import { agentTraceWsUrl } from '@/config/api'
import type { AgentTraceEvent } from '@/types/agentTrace'

type TraceStatus = 'idle' | 'connecting' | 'open' | 'closed' | 'error'

type TraceEnvelope = {
  type?: string
  session_id?: string
  payload?: AgentTraceEvent
}

export function useAgentTrace(sessionId: string | null) {
  const [events, setEvents] = useState<AgentTraceEvent[]>([])
  const [status, setStatus] = useState<TraceStatus>('idle')
  const activeTurnRef = useRef('')

  const clear = useCallback(() => {
    activeTurnRef.current = ''
    setEvents([])
  }, [])

  useEffect(() => {
    if (!sessionId) {
      setStatus('idle')
      return
    }

    setStatus('connecting')
    const socket = new WebSocket(agentTraceWsUrl(sessionId))
    socket.onopen = () => setStatus('open')
    socket.onerror = () => setStatus('error')
    socket.onclose = () => setStatus('closed')
    socket.onmessage = (message) => {
      try {
        const envelope = JSON.parse(message.data as string) as TraceEnvelope
        const event = envelope.type === 'agent.trace' ? envelope.payload : undefined
        if (!event?.turn_id || envelope.session_id !== sessionId) return
        if (event.phase === 'started') {
          activeTurnRef.current = event.turn_id
          setEvents([event])
          return
        }
        if (activeTurnRef.current && activeTurnRef.current !== event.turn_id) return
        activeTurnRef.current = event.turn_id
        setEvents((previous) => {
          if (previous.some((item) => item.turn_id === event.turn_id && item.sequence === event.sequence)) {
            return previous
          }
          return [...previous, event]
        })
      } catch {
        // Ignore malformed trace frames without interrupting the active command.
      }
    }
    return () => socket.close()
  }, [sessionId])

  return { events, status, clear }
}
