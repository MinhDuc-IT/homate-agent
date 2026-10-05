/** Backend Gateway WebSocket — log, HITL, scene, device snapshot. */
import { useEffect, useRef, useState } from 'react'

type WsStatus = 'idle' | 'connecting' | 'open' | 'closed' | 'error'

export function useWebSocket(url: string | null) {
  const [status, setStatus] = useState<WsStatus>('idle')
  const [lastMessage, setLastMessage] = useState<unknown>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!url) return
    setStatus('connecting')
    const ws = new WebSocket(url)
    wsRef.current = ws
    ws.onopen = () => setStatus('open')
    ws.onclose = () => setStatus('closed')
    ws.onerror = () => setStatus('error')
    ws.onmessage = (ev) => {
      try {
        setLastMessage(JSON.parse(ev.data))
      } catch {
        setLastMessage(ev.data)
      }
    }
    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [url])

  return { status, lastMessage, socket: wsRef }
}
