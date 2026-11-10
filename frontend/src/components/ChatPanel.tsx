import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useChat } from '../chat/context'
import { MAX_QUESTION_CHARS, plainAnswer } from '../chat/turn'
import ChatTurn from './ChatTurn'

const PLACEHOLDER = "What does your company or team work on? I'll point you to his closest work."
const DISCLOSURE =
  'Questions, answers and basic visit details, including internet protocol (IP) address and approximate location, are saved so this site can improve.'

const STARTERS = [
  'How did he connect a legacy system to modern reporting?',
  'How does he keep automation reliable?',
  'How does the trading system audit itself?',
  'What has he built with language models?',
]

const SHOW_COUNTER_AT = MAX_QUESTION_CHARS - 100

interface Props {
  variant: 'hero' | 'dock'
  onClose?: () => void
}

export default function ChatPanel({ variant, onClose }: Props) {
  const { messages, busy, send, clear } = useChat()
  const [draft, setDraft] = useState('')
  const scroller = useRef<HTMLDivElement>(null)
  const followLatest = useRef(true)

  useEffect(() => {
    const element = scroller.current
    if (element && followLatest.current) element.scrollTop = element.scrollHeight
  }, [messages])

  function onScroll() {
    const element = scroller.current
    if (!element) return
    followLatest.current = element.scrollHeight - element.scrollTop - element.clientHeight < 48
  }

  function submit(text: string) {
    if (!text.trim() || busy) return
    followLatest.current = true
    send(text)
    setDraft('')
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    submit(draft)
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit(draft)
    }
  }

  const empty = messages.length === 0
  const dock = variant === 'dock'
  const lastTurn = messages.at(-1)
  // Screen readers hear the finished answer once, not every streamed token.
  const announcement =
    lastTurn?.role === 'assistant' && lastTurn.state !== 'streaming' ? plainAnswer(lastTurn.content) : ''

  return (
    <section
      aria-label="Chat about his work"
      className={`flex flex-col rounded-xl border border-border bg-surface ${dock ? 'h-full shadow-2xl shadow-black/50' : ''}`}
    >
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-2.5">
        <h2 className="font-mono text-xs uppercase tracking-widest text-accent">Ask about his work</h2>
        <div className="flex items-center gap-3 font-mono text-xs text-muted">
          {!empty && !busy && (
            <button type="button" onClick={clear} className="hover:text-fg">clear</button>
          )}
          {onClose && (
            <button type="button" onClick={onClose} aria-label="Close chat" className="text-base leading-none hover:text-fg">×</button>
          )}
        </div>
      </div>

      <div
        ref={scroller}
        onScroll={onScroll}
        className={`overflow-y-auto px-4 py-4 ${dock ? 'min-h-0 flex-1 overscroll-contain' : 'max-h-[28rem]'}`}
      >
        {empty ? (
          <div>
            <p className="text-sm leading-relaxed text-muted">
              Answers come from his written case studies, with the sources shown.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {STARTERS.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => submit(question)}
                  className="rounded-full border border-border px-3 py-1 text-left text-[13px] text-muted transition-colors hover:border-accent/50 hover:text-fg"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            {messages.map((message) => <ChatTurn key={message.id} message={message} />)}
          </div>
        )}
      </div>

      <p className="sr-only" aria-live="polite">{announcement}</p>

      <form onSubmit={onSubmit} className="shrink-0 border-t border-border p-3">
        <div className="flex items-end gap-2">
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            maxLength={MAX_QUESTION_CHARS}
            rows={2}
            placeholder={PLACEHOLDER}
            aria-label="Your question"
            className="min-w-0 flex-1 resize-none rounded-md border border-border bg-bg px-3 py-2 text-base leading-snug text-fg placeholder:text-muted focus:border-accent focus:outline-none max-sm:h-[5.25rem]"
          />
          <button
            type="submit"
            disabled={busy || !draft.trim()}
            className="shrink-0 rounded-md bg-accent px-4 py-2 font-medium text-bg transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            Ask
          </button>
        </div>
        <div className="mt-2 flex items-start justify-between gap-3">
          <p className="text-[11px] leading-snug text-muted">{DISCLOSURE}</p>
          {draft.length >= SHOW_COUNTER_AT && (
            <p className="shrink-0 font-mono text-[11px] text-muted">{draft.length}/{MAX_QUESTION_CHARS}</p>
          )}
        </div>
      </form>
    </section>
  )
}
