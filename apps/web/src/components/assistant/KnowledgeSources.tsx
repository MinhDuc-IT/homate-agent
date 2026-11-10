import { useState } from 'react'
import { downloadSource, type KnowledgeSource } from '@/api/knowledge'

export function KnowledgeSources({ sources }: { sources?: KnowledgeSource[] }) {
  const [error, setError] = useState('')
  if (!sources?.length) return null
  return <details className="mt-2 rounded-lg border border-border bg-white p-2 text-xs">
    <summary className="cursor-pointer font-medium text-primary">Tài liệu đã tra cứu ({sources.length})</summary>
    {sources.map((source, index) => <div key={source.chunk_id} className="mt-3 border-t border-border-light pt-2">
      <p className="font-semibold">[{source.citation ?? index + 1}] {source.title} · Đoạn {source.ordinal + 1}</p>
      <p className="mt-1 whitespace-pre-wrap text-text-secondary">{source.content}</p>
      <button type="button" onClick={() => void downloadSource(source.document_id, source.filename).catch(err => setError(err instanceof Error ? err.message : 'Không tải được tài liệu'))} className="mt-2 text-primary underline">Tải tài liệu gốc</button>
    </div>)}
    {error && <p role="alert" className="text-danger">{error}</p>}
  </details>
}
