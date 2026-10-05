import { useEffect, useRef } from 'react'
import type { AgentTraceEvent } from '@/types/agentTrace'
import { cn } from '@/utils/cn'

const NODE_LABELS: Record<string, string> = {
  start: 'Nhận yêu cầu',
  start_turn: 'Khởi tạo lượt hội thoại',
  resolve_context: 'Khôi phục ngữ cảnh',
  preprocess: 'Chuẩn hóa yêu cầu',
  fast_parse: 'Phân tích lệnh nhanh',
  llm_plan: 'Lập kế hoạch',
  validate: 'Kiểm tra kế hoạch',
  policy: 'Đánh giá an toàn',
  clarify: 'Yêu cầu làm rõ',
  hitl: 'Yêu cầu xác nhận',
  execute: 'Thực thi thiết bị',
  respond: 'Tạo phản hồi',
  update_memory: 'Cập nhật ngữ cảnh',
  workflow: 'Workflow',
}

function formatDetails(details: Record<string, unknown>) {
  const entries = Object.entries(details).filter(([key]) => key !== 'label')
  if (!entries.length) return ''
  return entries
    .map(([key, value]) => `${key}: ${typeof value === 'string' ? value : JSON.stringify(value)}`)
    .join(' · ')
}

export function AgentTracePanel({
  events,
  status,
  dark = false,
  listClassName,
}: {
  events: AgentTraceEvent[]
  status: string
  dark?: boolean
  listClassName?: string
}) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'nearest' })
  }, [events])

  return (
    <section
      className={cn(
        'rounded-xl border p-3',
        dark ? 'border-white/10 bg-black/20 text-white' : 'border-sidebar-border bg-surface-subtle/60',
      )}
      aria-live="polite"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className={cn('text-xs font-semibold uppercase tracking-wide', dark ? 'text-cyan-200' : 'text-text-secondary')}>
          Agent trace
        </p>
        <span className={cn('text-[10px]', dark ? 'text-white/45' : 'text-text-muted')}>WS {status}</span>
      </div>
      {events.length ? (
        <ol className={cn('max-h-52 space-y-2 overflow-y-auto pr-1', listClassName)}>
          {events.map((event) => (
            <li key={`${event.turn_id}-${event.sequence}`} className="flex gap-2 text-xs">
              <span
                className={cn(
                  'mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full',
                  event.phase === 'error' ? 'bg-danger' : event.phase === 'started' ? 'bg-primary-light' : 'bg-success',
                )}
              />
              <div className="min-w-0">
                <p className={dark ? 'text-white/90' : 'text-text-primary'}>
                  {NODE_LABELS[event.node] || event.node}
                  <span className={dark ? 'ml-1 text-white/40' : 'ml-1 text-text-muted'}>{event.elapsed_ms}ms</span>
                </p>
                {formatDetails(event.details) ? (
                  <p className={cn('break-words text-[11px]', dark ? 'text-white/50' : 'text-text-secondary')}>
                    {formatDetails(event.details)}
                  </p>
                ) : null}
              </div>
            </li>
          ))}
          <div ref={endRef} />
        </ol>
      ) : (
        <p className={cn('text-xs', dark ? 'text-white/45' : 'text-text-muted')}>Chưa có bước xử lý nào.</p>
      )}
    </section>
  )
}
