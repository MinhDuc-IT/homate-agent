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
  kind?: 'plan'
  plan_version?: number
  conversation_id?: string
  recovery_required?: boolean
  steps?: { ordinal: number; summary: string; status: string; result?: Record<string, unknown> | null }[]
}
export interface ChatResult {
  conversation_id?: string
  conversation_version?: number
  dialogue_state?: string
  invalidated_plan_ids?: string[]
  invalidated_status?: string
  sources?: KnowledgeSource[]
  reply: string
  pending_actions: PendingAction[]
  completed_actions?: PendingAction[]
  trace: { tool: string; status: string }[]
}
export interface ConversationReference { id?: string; version?: number }
export interface StoredConversation {
  id: string; version: number; status: string; expired: boolean
  messages: (ChatMessage & { sources?: KnowledgeSource[] })[]
  plan: PendingAction | null
}
export async function fetchConversation(id: string) {
  return readJson<StoredConversation>(await apiFetch(`/api/dashboard/agent/conversations/${id}`))
}
export async function closeConversation(id: string) {
  return readJson<{ status: string }>(await apiFetch(`/api/dashboard/agent/conversations/${id}`, { method: 'DELETE' }))
}
export async function summarizePlan(action: PendingAction): Promise<string | null> {
  if (action.kind !== 'plan') return null
  try {
    const result = await readJson<{ reply: string }>(await apiFetch(`/api/ai/plans/${action.id}/summary`, { method: 'POST' }))
    return result.reply
  } catch { return null }
}
export function conversationKey(memberId: string, channel: 'chat' | 'voice') {
  return `homate.agent.${memberId}.${channel}`
}
export async function restoreConversation(memberId: string, channel: 'chat' | 'voice') {
  const id = localStorage.getItem(conversationKey(memberId, channel))
  if (!id) return null
  try { return await fetchConversation(id) }
  catch { localStorage.removeItem(conversationKey(memberId, channel)); return null }
}
export function storeConversation(memberId: string, channel: 'chat' | 'voice', result: ChatResult): ConversationReference {
  if (result.conversation_id) localStorage.setItem(conversationKey(memberId, channel), result.conversation_id)
  return { id: result.conversation_id, version: result.conversation_version }
}
export function reconcileActions(actions: PendingAction[], response: ChatResult) {
  return actions.map(action => response.invalidated_plan_ids?.includes(action.id)
    ? { ...action, status: response.invalidated_status ?? 'superseded' } : action)
}
export async function sendChat(text: string, history: ChatMessage[], requestId: string, conversation: ConversationReference = {}) {
  return readJson<ChatResult>(await apiFetch('/api/ai/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, history: history.slice(-12), request_id: requestId,
      conversation_id: conversation.id, conversation_version: conversation.version }),
  }))
}
export async function decideAction(action: PendingAction, approved: boolean) {
  const path = action.kind === 'plan' ? `plans/${action.id}` : `actions/${action.id}`
  return readJson<PendingAction>(await apiFetch(`/api/dashboard/agent/${path}/decision`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(action.kind === 'plan' ? { approved, version: action.plan_version } : { approved }),
  }))
}
export async function recoverPlan(action: PendingAction) {
  return readJson<PendingAction>(await apiFetch(`/api/dashboard/agent/plans/${action.id}/recover`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ version: action.plan_version, acknowledged: true }),
  }))
}
