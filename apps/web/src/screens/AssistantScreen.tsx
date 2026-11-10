import { KnowledgeSources } from '@/components/assistant/KnowledgeSources'
import type { KnowledgeSource } from '@/api/knowledge'
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { sendChat, decideAction, type ChatMessage, type PendingAction } from '@/api/agent'
import { TabletScreen } from '@/components/layout/TabletScreen'
import { Modal, ModalBody, ModalHeader } from '@/components/ui/Modal'
import { ActionCard } from '@/components/assistant/ActionCard'
import { actionStatusLabels } from '@/components/assistant/actionStatus'
import { ChatIcon, MessageContent } from '@/components/assistant/ChatPrimitives'
import { useSession } from '@/context/SessionContext'

interface ConversationMessage extends ChatMessage {
  id: string
  time: string
  delivery?: 'sending' | 'sent' | 'failed'
  actions?: PendingAction[]
  sources?: KnowledgeSource[]
}
const suggestions = [
  { icon: 'bulb', title: 'Kiểm tra thiết bị', text: 'Những thiết bị nào đang bật?' },
  { icon: 'energy', title: 'Theo dõi điện năng', text: 'Phòng khách dùng bao nhiêu điện trong 7 ngày qua?' },
  { icon: 'scene', title: 'Khám phá kịch bản', text: 'Tôi đang có những kịch bản nào?' },
  { icon: 'calendar', title: 'Xem lịch tự động', text: 'Liệt kê các lịch tự động của tôi.' },
] as const
const time = () => new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })

export function AssistantScreen() {
  const { session } = useSession()
  const [messages, setMessages] = useState<ConversationMessage[]>([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [sending, setSending] = useState(false)
  const [decidingId, setDecidingId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [newChatOpen, setNewChatOpen] = useState(false)
  const [showJump, setShowJump] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const nearBottom = useRef(true)
  const inFlight = useRef(false)

  useEffect(() => {
    const element = inputRef.current
    if (element) { element.style.height = 'auto'; element.style.height = `${Math.min(element.scrollHeight, 136)}px` }
  }, [text])
  useEffect(() => {
    if (!messages.length && scrollRef.current) { scrollRef.current.scrollTop = 0; return }
    if (nearBottom.current && scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages, sending])

  async function send(input: string, retryId?: string) {
    if (!input.trim() || inFlight.current) return
    const content = input.trim()
    const id = retryId ?? crypto.randomUUID()
    const history = messages.filter(message => message.id !== retryId && message.delivery !== 'failed' && message.delivery !== 'sending').map(({ role, content }) => ({ role, content }))
    inFlight.current = true
    nearBottom.current = true
    setShowJump(false); setBusy(true); setSending(true); setError(''); setText('')
    const userMessage: ConversationMessage = { id, role: 'user', content, time: time(), delivery: 'sending' }
    setMessages(previous => retryId ? previous.map(message => message.id === retryId ? userMessage : message) : [...previous, userMessage])
    try {
      const response = await sendChat(content, history, id)
      setMessages(previous => [...previous.map(message => message.id === id ? { ...message, delivery: 'sent' as const } : message), {
        id: crypto.randomUUID(), role: 'assistant', content: response.reply, time: time(), actions: response.pending_actions, sources: response.sources,
      }])
    } catch (err) {
      setMessages(previous => previous.map(message => message.id === id ? { ...message, delivery: 'failed' } : message))
      setText(draft => draft || content)
      setError(err instanceof Error ? err.message : 'Không gửi được tin nhắn. Vui lòng thử lại.')
    } finally {
      inFlight.current = false; setBusy(false); setSending(false)
      inputRef.current?.focus()
    }
  }
  function submit(event: FormEvent) {
    event.preventDefault()
    const last = messages[messages.length - 1]
    void send(text, last?.delivery === 'failed' && last.content === text.trim() ? last.id : undefined)
  }
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      if (text.trim() && !busy) inputRef.current?.form?.requestSubmit()
    }
  }
  async function decide(action: PendingAction, approved: boolean) {
    if (inFlight.current) return
    inFlight.current = true
    setBusy(true); setDecidingId(action.id); setError('')
    try {
      const result = await decideAction(action.id, approved)
      const status = actionStatusLabels[result.status] ?? result.status
      setMessages(previous => [...previous.map(message => ({ ...message, actions: message.actions?.map(item => item.id === action.id ? result : item) })), {
        id: crypto.randomUUID(), role: 'assistant', content: `${action.summary}: ${status}.`, time: time(),
      }])
    } catch (err) { setError(err instanceof Error ? err.message : 'Không xử lý được xác nhận. Vui lòng kiểm tra trạng thái trước khi thử lại.') }
    finally { inFlight.current = false; setBusy(false); setDecidingId(null) }
  }
  function chooseSuggestion(value: string) { setText(value); inputRef.current?.focus() }
  function reset() {
    setMessages([]); setText(''); setError(''); setNewChatOpen(false); setShowJump(false)
    nearBottom.current = true
    inputRef.current?.focus()
  }

  return <TabletScreen>
    <section className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-2xl border border-border bg-[#FCFDFB] shadow-card">
      <header className="flex shrink-0 items-center justify-between gap-2 border-b border-border-light bg-white px-4 py-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary text-white"><ChatIcon name="sparkle" className="h-5 w-5" /></span>
          <div className="min-w-0"><h1 className="truncate text-sm font-semibold text-primary sm:text-base">Trợ lý HomeMate</h1><p className="mt-0.5 truncate text-[11px] text-text-muted">Cùng bạn chăm sóc ngôi nhà</p></div>
        </div>
        <button type="button" disabled={busy || !messages.length} onClick={() => setNewChatOpen(true)} aria-label="Cuộc trò chuyện mới" title="Cuộc trò chuyện mới" className="flex shrink-0 items-center gap-2 rounded-xl border border-border px-2.5 py-2 text-xs font-medium text-text-secondary transition hover:border-primary/30 hover:bg-primary-subtle focus-visible:outline-2 focus-visible:outline-primary disabled:opacity-35"><ChatIcon name="plus" /><span className="hidden sm:inline">Cuộc trò chuyện mới</span></button>
      </header>

      <div className="relative flex min-h-0 flex-1 flex-col">
        <div ref={scrollRef} onScroll={() => {
          const element = scrollRef.current
          if (!element) return
          nearBottom.current = element.scrollHeight - element.scrollTop - element.clientHeight < 90
          setShowJump(!nearBottom.current)
        }} className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-5 sm:px-6" role="log" aria-label="Cuộc trò chuyện với HomeMate" aria-live="polite" aria-relevant="additions">
          {!messages.length ? <div className="mx-auto flex min-h-full w-full max-w-xl flex-col items-center justify-center py-4 sm:py-8">
            <div className="relative mb-6 flex h-20 w-20 items-center justify-center rounded-[28px] border border-[#D8E5DA] bg-gradient-to-br from-[#EDF5EB] to-[#E0ECE3] text-primary shadow-[0_8px_30px_-12px_#1e4d3840]"><ChatIcon name="sparkle" className="h-9 w-9" /><span className="absolute -right-1 -bottom-1 flex h-6 w-6 items-center justify-center rounded-full border-4 border-[#FCFDFB] bg-primary text-white"><ChatIcon name="check" className="h-3 w-3" /></span></div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-primary-light">Ngôi nhà trong tầm tay</p>
            <h2 className="mt-3 text-center font-display text-2xl font-semibold tracking-tight text-text-primary sm:text-[30px]">Hôm nay, tôi có thể giúp gì?</h2>
            <p className="mt-3 max-w-sm text-center text-xs leading-6 text-text-secondary">Chào {session?.memberName ?? 'bạn'}, hãy hỏi về ngôi nhà hoặc cho tôi biết bạn muốn làm gì.</p>
            <div className="mt-7 grid w-full grid-cols-1 gap-2.5 min-[420px]:grid-cols-2">
              {suggestions.map(suggestion => <button type="button" key={suggestion.title} onClick={() => chooseSuggestion(suggestion.text)} className="group flex items-start gap-3 rounded-2xl border border-border bg-white p-3.5 text-left transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-card focus-visible:outline-2 focus-visible:outline-primary motion-reduce:transform-none">
                <span className="rounded-xl bg-surface-subtle p-2 text-primary transition group-hover:bg-primary-subtle"><ChatIcon name={suggestion.icon} /></span>
                <span className="min-w-0"><span className="block text-xs font-semibold text-text-primary">{suggestion.title}</span><span className="mt-1 block text-[11px] leading-relaxed text-text-muted">{suggestion.text}</span></span>
              </button>)}
            </div>
          </div> : <div className="mx-auto w-full max-w-2xl space-y-6 pb-2">
            <p className="text-center text-[10px] font-medium uppercase tracking-widest text-text-muted">Cuộc trò chuyện hiện tại</p>
            {messages.map(message => <article key={message.id} aria-label={message.role === 'user' ? 'Tin nhắn của bạn' : 'Tin nhắn của HomeMate'} className={`flex gap-2.5 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
              {message.role === 'assistant' && <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-primary-subtle text-primary"><ChatIcon name="sparkle" className="h-4 w-4" /></span>}
              <div className={`min-w-0 ${message.role === 'user' ? 'max-w-[85%]' : 'max-w-[calc(100%-2.5rem)] flex-1'}`}>
                <div className={`mb-1.5 flex items-center gap-2 text-[10px] ${message.role === 'user' ? 'justify-end' : ''}`}><span className="font-semibold text-text-secondary">{message.role === 'user' ? 'Bạn' : 'HomeMate'}</span><span className="text-text-muted">{message.time}</span></div>
                <div className={`rounded-2xl px-4 py-3 text-[13px] leading-6 ${message.role === 'user' ? 'rounded-tr-md bg-primary text-white' : 'rounded-tl-md border border-border-light bg-white text-text-primary'}`}><MessageContent text={message.content} /></div>
                <KnowledgeSources sources={message.sources} />
                {message.delivery === 'failed' && <div className="mt-2 flex items-center justify-end gap-2 text-[11px] text-danger"><span>Chưa gửi được</span><button type="button" disabled={busy} onClick={() => void send(message.content, message.id)} className="flex items-center gap-1 rounded-md px-1.5 py-1 font-semibold hover:bg-danger-light disabled:opacity-40"><ChatIcon name="retry" className="h-3 w-3" />Thử lại</button></div>}
                {message.actions?.map(action => <ActionCard key={action.id} action={action} disabled={busy} processing={decidingId === action.id} onDecide={(item, approved) => void decide(item, approved)} />)}
              </div>
            </article>)}
            {sending && <div className="flex items-start gap-2.5" role="status"><span className="flex h-7 w-7 items-center justify-center rounded-xl bg-primary-subtle text-primary"><ChatIcon name="sparkle" /></span><div className="rounded-2xl rounded-tl-md border border-border-light bg-white px-4 py-3"><span className="flex items-center gap-1 text-primary" aria-hidden="true">{[0, 1, 2].map(i => <span key={i} style={{ animationDelay: `${i * 150}ms` }} className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary/60 motion-reduce:animate-none" />)}</span><p className="mt-2 text-[11px] text-text-muted">HomeMate đang xử lý…</p></div></div>}
          </div>}
        </div>
        {showJump && <button type="button" onClick={() => { nearBottom.current = true; setShowJump(false); scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight }) }} className="absolute bottom-3 left-1/2 flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-border bg-white px-3 py-2 text-xs text-primary shadow-elevated"><ChatIcon name="down" className="h-3.5 w-3.5" />Xuống cuối</button>}
      </div>

      <div className="shrink-0 bg-gradient-to-t from-white to-[#FCFDFB] px-3 pt-2 pb-3 sm:px-6 sm:pb-4">
        <div className="mx-auto max-w-2xl">
          {error && <div role="alert" className="mb-2 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-xs leading-5 text-red-700">{error}</div>}
          <form onSubmit={submit} className="rounded-2xl border border-[#D9E3D9] bg-white p-2 shadow-[0_3px_16px_-6px_#1e4d381c] transition focus-within:border-primary/45 focus-within:ring-2 focus-within:ring-primary/5">
            <label htmlFor="assistant-message" className="sr-only">Tin nhắn cho HomeMate</label>
            <textarea id="assistant-message" ref={inputRef} value={text} rows={1} maxLength={4000} onChange={event => setText(event.target.value)} onKeyDown={handleKeyDown} placeholder="Bạn muốn làm gì với ngôi nhà?" className="block max-h-[136px] min-h-11 w-full resize-none overflow-y-auto border-0 bg-transparent px-2 py-2.5 text-sm leading-6 text-text-primary outline-none placeholder:text-text-muted" />
            <div className="flex items-center justify-between gap-2 px-1 pt-1"><span className="flex items-center gap-1.5 text-[10px] text-text-muted"><ChatIcon name="shield" className="h-3 w-3" />Bạn xác nhận trước khi thực hiện</span><button type="submit" aria-label="Gửi" title="Gửi tin nhắn" disabled={busy || !text.trim()} className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-white transition hover:bg-primary-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:bg-[#E8EDE6] disabled:text-[#AAB7AC]"><ChatIcon name="send" className="h-4 w-4" /></button></div>
          </form>
          <p className="mt-2 text-center text-[10px] text-text-muted"><span className="hidden sm:inline">Enter để gửi · Shift + Enter để xuống dòng · </span>Hãy kiểm tra nội dung đề xuất trước khi xác nhận.</p>
        </div>
      </div>
    </section>
    <Modal open={newChatOpen} onClose={() => setNewChatOpen(false)} maxWidth="sm">
      <ModalHeader title="Bắt đầu cuộc trò chuyện mới?" />
      <ModalBody><p className="text-sm leading-6 text-text-secondary">Nội dung trò chuyện hiện tại sẽ được xóa khỏi màn hình. Các yêu cầu chưa xác nhận sẽ tự hết hạn.</p><div className="mt-5 flex justify-end gap-2"><button type="button" onClick={() => setNewChatOpen(false)} className="rounded-xl border border-border px-4 py-2 text-sm">Quay lại</button><button type="button" onClick={reset} className="rounded-xl bg-primary px-4 py-2 text-sm text-white">Bắt đầu mới</button></div></ModalBody>
    </Modal>
  </TabletScreen>
}
