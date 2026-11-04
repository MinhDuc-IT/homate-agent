import type { ReactNode } from 'react'

const paths = {
  sparkle: 'm12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4L12 3Zm7-1v4m-2-2h4',
  send: 'M12 19V5m-6 6 6-6 6 6',
  plus: 'M12 5v14M5 12h14',
  bulb: 'M9 18h6m-5 3h4M8.1 14.5a6 6 0 1 1 7.8 0c-.8.7-.9 1.5-.9 2.5H9c0-1-.1-1.8-.9-2.5Z',
  energy: 'm13 2-9 12h7l-1 8L21 9h-8l1-7',
  scene: 'm12 3 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 16l9 5 9-5',
  calendar: 'M8 2v4m8-4v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2Zm3 10h3m-3 3h6',
  check: 'm5 12 4 4L19 6',
  clock: 'M12 8v5l3 2m6-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  close: 'm6 6 12 12M6 18 18 6',
  retry: 'M3 10a9 9 0 1 1 2 8M3 4v6h6',
  down: 'M12 4v16m-6-6 6 6 6-6',
  shield: 'M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6l-8-3Zm-4 9 3 3 5-6',
} as const

export function ChatIcon({ name, className = 'h-4 w-4' }: { name: keyof typeof paths; className?: string }) {
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>
}

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, index) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={index} className="font-semibold">{part.slice(2, -2)}</strong> :
      part.startsWith('`') && part.endsWith('`') ? <code key={index} className="rounded bg-black/5 px-1 py-0.5 text-[0.9em]">{part.slice(1, -1)}</code> : part)
}

/** A deliberately small, text-only renderer: emphasis, paragraphs and lists; no HTML. */
export function MessageContent({ text }: { text: string }) {
  return <div className="space-y-2 break-words [overflow-wrap:anywhere]">{text.split(/\n\s*\n/).map((block, index) => {
    const lines = block.split('\n')
    if (lines.every(line => /^\s*(?:[-*]|\d+[.)])\s/.test(line))) {
      const ordered = /^\s*\d/.test(lines[0])
      const List = ordered ? 'ol' : 'ul'
      return <List key={index} className={`space-y-1 pl-5 ${ordered ? 'list-decimal' : 'list-disc'}`}>{lines.map((line, i) => <li key={i}>{inline(line.replace(/^\s*(?:[-*]|\d+[.)])\s+/, ''))}</li>)}</List>
    }
    return <p key={index} className="whitespace-pre-wrap">{inline(block)}</p>
  })}</div>
}
