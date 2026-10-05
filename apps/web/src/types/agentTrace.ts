export type AgentTraceEvent = {
  turn_id: string
  sequence: number
  node: string
  phase: 'started' | 'completed' | 'error'
  elapsed_ms: number
  total_ms: number
  details: Record<string, unknown>
}
