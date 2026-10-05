/** MQTT-over-WebSocket (broker :9001) — subscribe device state trực tiếp. */
import { useEffect, useState } from 'react'

type MqttStatus = 'idle' | 'connecting' | 'subscribed' | 'error'

/**
 * Stub hook — gắn MQTT.js / mqtt over WS khi broker sẵn sàng.
 * Topic mẫu: home/+/+/+/state
 */
export function useMqttSubscribe(brokerUrl: string | null, topic: string) {
  const [status, setStatus] = useState<MqttStatus>('idle')
  const [payload, setPayload] = useState<unknown>(null)

  useEffect(() => {
    if (!brokerUrl) return
    setStatus('connecting')
    // Placeholder until mqtt.js client is wired
    const timer = window.setTimeout(() => {
      setStatus('subscribed')
      setPayload(null)
    }, 0)
    return () => {
      window.clearTimeout(timer)
      setStatus('idle')
    }
  }, [brokerUrl, topic])

  return { status, payload }
}
