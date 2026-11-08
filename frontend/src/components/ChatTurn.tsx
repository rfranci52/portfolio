import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useChat } from '../chat/context'
import { webHref } from '../chat/links'
import type { ChatMessage, FeedbackValue, Passage, RelatedLink, Sources, Stage } from '../chat/types'
import SafeMarkdown from './SafeMarkdown'
import SiteLink from './SiteLink'

const label = 'font-mono text-[11px] uppercase tracking-widest text-muted'
const sourceLink = 'text-fg underline decoration-border underline-offset-2 hover:text-accent hover:decoration-accent'

const OVER_LIMIT_TEXT =
  'The chat has reached its limit for today. The project pages and the live demo are still open.'
const ERROR_TEXT = 'The chat could not answer that one. Try again in a moment.'
const NETWORK_TEXT = 'The connection dropped before the answer finished.'

function Passages({ items }: { items: Passage[] }) {
  const [expanded, setExpanded] = useState(false)
  const shown = expanded ? items : items.slice(0, 3)
  return (
    <div>
      <p className={label}>Passages found</p>
      <ul className="mt-2 space-y-1.5">
        {shown.map((passage) => (
          <li key={passage.id} className="rounded-md border border-border bg-bg/40 px-2.5 py-1.5 text-xs text-muted">
            <span className="break-words">
              <SiteLink url={passage.url} className={sourceLink}>{passage.title}</SiteLink>
              {passage.section && <span> / {passage.section}</span>}
            </span>
            {expanded && passage.snippet && <p className="mt-1 break-words leading-relaxed">{passage.snippet}</p>}
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="mt-1.5 font-mono text-[11px] text-muted hover:text-fg"
      >
        {expanded ? 'show less' : items.length > 3 ? `show all ${items.length} with snippets` : 'show snippets'}
      </button>
    </div>
  )
}

function StageLine({ stage }: { stage: Stage }) {
  let text = 'Searching his written work'
  if (stage === 'writing') text = 'Writing the answer'
  if (stage === 'looking_up') text = 'Looking up public information'
  return (
    <p role="status" className="flex items-center gap-2 font-mono text-xs text-accent">
      <span className="relative flex h-2 w-2 shrink-0">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent/60" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
      </span>
      <span className="min-w-0 break-words">{text}…</span>
    </p>
  )
}

function SourceGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <p className={label}>{title}</p>
      <ul className="mt-1.5 space-y-1 text-[13px] text-muted">{children}</ul>
    </div>
  )
}

function SourceList({ sources, related }: { sources: Sources; related: RelatedLink[] }) {
  const webLinks = sources.web.flatMap((source) => {
    const href = webHref(source.url)
    if (!href) return []
    // Some pages have machine-generated titles, so fall back to the site's name.
    const readable = source.title && !/[0-9a-f]{16}/i.test(source.title)
    return [{ title: readable ? source.title : new URL(href).hostname, href }]
  })
  // Related entries repeat work sources when both come from the same passage.
  const workUrls = new Set(sources.work.map((source) => source.url))
  const extraRelated = related.filter((item) => !workUrls.has(item.url))

  if (sources.work.length + webLinks.length + extraRelated.length === 0) return null

  return (
    <div className="space-y-3 border-t border-border pt-3">
      {sources.work.length > 0 && (
        <SourceGroup title="From his work">
          {sources.work.map((source, i) => (
            <li key={i} className="break-words">
              <SiteLink url={source.url} className={sourceLink}>{source.title}</SiteLink>
              {source.section && <span> / {source.section}</span>}
            </li>
          ))}
        </SourceGroup>
      )}
      {webLinks.length > 0 && (
        <SourceGroup title="From the web">
          {webLinks.map((source, i) => (
            <li key={i} className="break-words">
              <a href={source.href} target="_blank" rel="noreferrer" className={sourceLink}>{source.title}</a>
            </li>
          ))}
        </SourceGroup>
      )}
      {extraRelated.length > 0 && (
        <SourceGroup title="Related work">
          {extraRelated.map((item, i) => (
            <li key={i} className="break-words">
              <SiteLink url={item.url} className={sourceLink}>{item.title}</SiteLink>
            </li>
          ))}
        </SourceGroup>
      )}
    </div>
  )
}

// The server rounds these to the nearest second and cent.
function formatMs(ms: number): string {
  return ms >= 1000 ? `${Math.round(ms / 1000)} s` : 'under 1 s'
}

function formatCost(usd: number): string {
  return usd >= 0.01 ? `$${usd.toFixed(2)}` : 'under $0.01'
}

function RunDetails({ turn }: { turn: ChatMessage }) {
  // A fixed reply never reached a model, so there is nothing to report.
  if (!turn.model) return null
  const parts = [turn.model]
  if (turn.costUsd !== undefined && turn.costUsd !== null) parts.push(formatCost(turn.costUsd))
  if (turn.ms !== undefined && turn.ms !== null) parts.push(formatMs(turn.ms))
  return <p className="min-w-0 break-words font-mono text-[11px] text-muted">{parts.join(' · ')}</p>
}

const THUMB_PATHS: Record<FeedbackValue, string> = {
  up: 'M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3',
  down: 'M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17',
}

function Thumb({ turn, value }: { turn: ChatMessage; value: FeedbackValue }) {
  const { rate } = useChat()
  const active = turn.feedback === value
  return (
    <button
      type="button"
      aria-label={value === 'up' ? 'Helpful answer' : 'Unhelpful answer'}
      aria-pressed={active}
      onClick={() => rate(turn.id, value)}
      className={`rounded p-1 transition-colors hover:text-fg ${active ? 'text-accent' : 'text-muted'}`}
    >
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d={THUMB_PATHS[value]} />
      </svg>
    </button>
  )
}

function Notice({ tone, children }: { tone: 'neutral' | 'error'; children: ReactNode }) {
  const color = tone === 'error' ? 'border-red-400/40 bg-red-400/5' : 'border-border bg-elevated'
  return <div role="alert" className={`rounded-md border px-3 py-2.5 text-sm text-fg ${color}`}>{children}</div>
}

function AssistantTurn({ turn }: { turn: ChatMessage }) {
  const { busy, retry } = useChat()
  const streaming = turn.state === 'streaming'
  const finished = turn.state === 'done'

  const retryButton = (
    <button
      type="button"
      disabled={busy}
      onClick={() => retry(turn.id)}
      className="mt-2 block font-mono text-xs text-accent hover:underline disabled:opacity-50"
    >
      try again
    </button>
  )

  return (
    <div className="space-y-3">
      {turn.passages && turn.passages.length > 0 && <Passages items={turn.passages} />}
      {turn.content && <SafeMarkdown text={turn.content} streaming={streaming} />}
      {streaming && turn.stage && <StageLine stage={turn.stage} />}

      {turn.state === 'over_limit' && (
        <Notice tone="neutral">
          <p className={label}>Daily limit reached</p>
          <p className="mt-1 text-muted">{turn.notice || OVER_LIMIT_TEXT}</p>
          <p className="mt-2 font-mono text-xs">
            <a href="https://demo.rakimfrancis.com" target="_blank" rel="noreferrer" className="text-accent hover:underline">live demo →</a>
            <Link to="/projects" className="ml-4 text-muted hover:text-fg">projects →</Link>
            <Link to="/contact" className="ml-4 text-muted hover:text-fg">contact →</Link>
          </p>
        </Notice>
      )}
      {turn.state === 'error' && (
        <Notice tone="error">
          <p className="text-muted">{turn.notice || ERROR_TEXT}</p>
          {retryButton}
        </Notice>
      )}
      {turn.state === 'network' && (
        <Notice tone="error">
          <p className={label}>Connection lost</p>
          <p className="mt-1 text-muted">{NETWORK_TEXT}</p>
          {retryButton}
        </Notice>
      )}

      {turn.state === 'done' && turn.sources && (
        <SourceList sources={turn.sources} related={turn.related ?? []} />
      )}
      {finished && (
        <div className="flex items-center justify-between gap-3">
          <RunDetails turn={turn} />
          {turn.turnId && (
            <div className="ml-auto flex shrink-0 gap-0.5">
              <Thumb turn={turn} value="up" />
              <Thumb turn={turn} value="down" />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ChatTurn({ message }: { message: ChatMessage }) {
  if (message.role === 'assistant') return <AssistantTurn turn={message} />
  return (
    <div className="flex justify-end">
      <p className="max-w-[85%] whitespace-pre-wrap break-words rounded-lg bg-elevated px-3 py-2 text-[15px] leading-relaxed text-fg">
        {message.content}
      </p>
    </div>
  )
}
