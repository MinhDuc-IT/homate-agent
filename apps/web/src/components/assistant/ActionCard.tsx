import { useEffect, useState } from 'react'
import type { PendingAction } from '@/api/agent'
import { ChatIcon } from './ChatPrimitives'
import { actionStatusLabels } from './actionStatus'

export function ActionCard({ action, disabled, processing, onDecide }: {
  action: PendingAction; disabled: boolean; processing: boolean
  onDecide: (action: PendingAction, approved: boolean) => void
}) {
  const [now, setNow] = useState(Date.now)
  const deadline = new Date(action.expires_at).getTime()
  useEffect(() => {
    if (action.status !== 'pending') return
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [action.status, action.expires_at])
  const seconds = Math.max(0, Math.ceil((deadline - now) / 1000))
  const status = action.status === 'pending' && seconds === 0 ? 'expired' : action.status
  const pending = status === 'pending'
  const executed = status === 'executed'
  const review = Array.isArray(action.arguments.review) ? action.arguments.review : []
  return <section aria-label={`Thao tác: ${action.summary}`} className={`mt-3 overflow-hidden rounded-2xl border ${pending ? 'border-[#D9E5DC] bg-white' : 'border-border-light bg-surface-subtle'}`}>
    <div className="flex items-start gap-3 p-4">
      <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${pending || executed ? 'bg-primary-subtle text-primary' : 'bg-white text-text-muted'}`}><ChatIcon name={pending ? 'shield' : executed ? 'check' : status === 'expired' || status === 'executing' ? 'clock' : 'close'} /></div>
      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted">{pending ? 'Cần bạn xác nhận' : 'Kết quả thao tác'}</p>
        <h3 className="mt-1 break-words text-sm font-semibold text-text-primary">{action.summary}</h3>
        {review.length > 0 && <ul className="mt-2 space-y-1 text-xs leading-relaxed text-text-secondary">{review.map((line, index) => <li key={index}>{String(line)}</li>)}</ul>}
        {pending ? <p className="mt-3 flex items-center gap-1.5 text-[11px] text-text-muted"><ChatIcon name="clock" className="h-3 w-3" />Còn {seconds} giây để xác nhận</p> : <p className={`mt-2 text-xs font-medium ${executed ? 'text-primary' : 'text-text-secondary'}`}>{actionStatusLabels[status] ?? status}</p>}
        {status === 'expired' && <p className="mt-1 text-xs text-text-muted">Gửi lại yêu cầu nếu bạn vẫn muốn thực hiện.</p>}
        {(status === 'failed' || status === 'executing') && <p className="mt-1 text-xs text-text-muted">Kiểm tra trạng thái thực tế trước khi gửi yêu cầu mới.</p>}
      </div>
    </div>
    {pending && <div className="flex flex-wrap items-center justify-end gap-2 border-t border-border-light bg-surface-subtle px-4 py-3">
      <button type="button" disabled={disabled} onClick={() => onDecide(action, false)} className="rounded-xl border border-border bg-white px-3.5 py-2 text-xs font-medium text-text-secondary transition hover:bg-surface-hover focus-visible:outline-2 focus-visible:outline-primary disabled:opacity-40">Từ chối</button>
      <button type="button" disabled={disabled} onClick={() => onDecide(action, true)} className="flex items-center gap-1.5 rounded-xl bg-primary px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-primary-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:opacity-40"><ChatIcon name="check" className="h-3.5 w-3.5" />{processing ? 'Đang xử lý…' : 'Xác nhận'}</button>
    </div>}
  </section>
}
