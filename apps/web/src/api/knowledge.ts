import { apiFetch, parseError } from './http'

export interface KnowledgeSource {
  chunk_id: string; document_id: string; title: string; filename: string
  content: string; ordinal: number; citation?: number
  metadata: Record<string, unknown>
}
const base = '/api/rag'
export async function downloadSource(id: string, filename: string) {
  const response = await apiFetch(`${base}/documents/${id}/source`)
  if (!response.ok) throw new Error(await parseError(response))
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename
  anchor.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
