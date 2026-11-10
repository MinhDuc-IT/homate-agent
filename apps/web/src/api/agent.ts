import type { KnowledgeSource } from './knowledge'
import { apiFetch, readJson } from '@/api/http'

export interface ChatMessage { role: 'user' | 'assistant'; content: string }
export interface PendingAction {
  id: string
  summary: string
  tool: string
  arguments: Record<string, unknown>
  expires_at: string
  status: string
  result?: Record<string, unknown> | null
}
export interface ChatResult {
  sources?: KnowledgeSource[]
  reply: string
  pending_actions: PendingAction[]
  trace: { tool: string; status: string }[]
}
export async function sendChat(text: string, history: ChatMessage[], requestId: string) {
  return readJson<ChatResult>(await apiFetch('/api/ai/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, history: history.slice(-12), request_id: requestId }),
  }))
}
export async function decideAction(id: string, approved: boolean) {
  return readJson<PendingAction>(await apiFetch(`/api/dashboard/agent/actions/${id}/decision`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ approved }),
  }))
}
