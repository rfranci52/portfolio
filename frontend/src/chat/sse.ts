import type {
  ChatEvent,
  ChatRequest,
  Passage,
  RelatedLink,
  Sources,
  Stage,
  StreamEnd,
} from './types'

// If no bytes arrive for this long the stream is treated as dropped.
// It sits above the function's 60 second ceiling.
const IDLE_TIMEOUT_MS = 75_000

export interface SseParser {
  push(chunk: string): string[]
  flush(): string[]
}

function extractData(block: string): string | null {
  const lines: string[] = []
  for (const line of block.split('\n')) {
    // Comments (":") and other fields (event, id, retry) carry nothing for this client.
    if (!line.startsWith('data:')) continue
    const value = line.slice(5)
    lines.push(value.startsWith(' ') ? value.slice(1) : value)
  }
  return lines.length > 0 ? lines.join('\n') : null
}

/**
 * Incremental Server-Sent Events parser. Network chunks can end anywhere,
 * including between "\r" and "\n", so text is buffered until a blank line
 * closes the event.
 */
export function createSseParser(): SseParser {
  let buffer = ''
  let heldCarriageReturn = false

  function drain(): string[] {
    const events: string[] = []
    let end = buffer.indexOf('\n\n')
    while (end !== -1) {
      const data = extractData(buffer.slice(0, end))
      buffer = buffer.slice(end + 2)
      if (data !== null) events.push(data)
      end = buffer.indexOf('\n\n')
    }
    return events
  }

  return {
    push(chunk) {
      let text = heldCarriageReturn ? `\r${chunk}` : chunk
      heldCarriageReturn = text.endsWith('\r')
      if (heldCarriageReturn) text = text.slice(0, -1)
      buffer += text.replace(/\r\n?/g, '\n')
      return drain()
    },
    // End of stream: a last event may have lost its closing blank line.
    flush() {
      const rest = buffer
      buffer = ''
      heldCarriageReturn = false
      const data = extractData(rest)
      return data === null ? [] : [data]
    },
  }
}

type Fields = Record<string, unknown>

const isFields = (value: unknown): value is Fields =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const text = (value: unknown): string => (typeof value === 'string' ? value : '')

function numberOrNull(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

const rows = (value: unknown): Fields[] => (Array.isArray(value) ? value.filter(isFields) : [])

function readPassages(value: unknown): Passage[] {
  return rows(value).map((row, index) => ({
    id: text(row.id) || String(index),
    title: text(row.title),
    section: text(row.section),
    url: text(row.url),
    snippet: text(row.snippet),
  }))
}

function readSources(value: unknown): Sources {
  const fields = isFields(value) ? value : {}
  return {
    work: rows(fields.work).map((row) => ({
      title: text(row.title),
      section: text(row.section),
      url: text(row.url),
    })),
    web: rows(fields.web).map((row) => ({ title: text(row.title), url: text(row.url) })),
  }
}

function readRelated(value: unknown): RelatedLink[] {
  return rows(value)
    .map((row) => ({ title: text(row.title), url: text(row.url) }))
    .filter((row) => row.title !== '' && row.url !== '')
}

function readStage(value: unknown): Stage | null {
  return value === 'searching' || value === 'looking_up' || value === 'writing' ? value : null
}

/** Validates one event. Returns null for malformed or unknown events instead of throwing. */
export function parseChatEvent(data: string): ChatEvent | null {
  let raw: unknown
  try {
    raw = JSON.parse(data)
  } catch {
    return null
  }
  if (!isFields(raw)) return null

  switch (raw.type) {
    case 'status': {
      const stage = readStage(raw.stage)
      return stage ? { type: 'status', stage } : null
    }
    case 'passages':
      return { type: 'passages', items: readPassages(raw.items) }
    case 'lookup':
      return { type: 'lookup' }
    case 'delta':
      return { type: 'delta', text: text(raw.text) }
    case 'retract':
      return { type: 'retract', text: text(raw.text) }
    case 'error':
      return { type: 'error', message: text(raw.message), code: text(raw.code) }
    case 'done':
      return {
        type: 'done',
        turnId: text(raw.turn_id),
        model: text(raw.model),
        costUsd: numberOrNull(raw.cost_usd),
        ms: numberOrNull(raw.ms),
        cited: Array.isArray(raw.cited) ? raw.cited.filter((id) => typeof id === 'string') : [],
        sources: readSources(raw.sources),
        related: readRelated(raw.related),
        signature: text(raw.signature),
      }
    default:
      return null
  }
}

function endsStream(event: ChatEvent): boolean {
  return event.type === 'done' || event.type === 'error'
}

async function readFailureMessage(res: Response): Promise<string> {
  try {
    const body = (await res.text()).trim()
    const parser = createSseParser()
    const payloads = body.startsWith('data:') ? parser.push(`${body}\n\n`) : [body]
    for (const payload of payloads) {
      const parsed: unknown = JSON.parse(payload)
      if (isFields(parsed)) {
        const message = text(parsed.message) || text(parsed.text) || text(parsed.detail)
        if (message) return message
      }
    }
  } catch {
    // A body that is not JSON carries nothing worth showing.
  }
  return ''
}

/**
 * POSTs to /api/chat and reads the event stream with a fetch reader, because
 * EventSource cannot send a POST body. Never rejects: every failure comes back
 * as a StreamEnd so the interface always reaches a visible state.
 */
export async function streamChat(
  request: ChatRequest,
  onEvent: (event: ChatEvent) => void,
): Promise<StreamEnd> {
  const controller = new AbortController()
  let idleTimer = setTimeout(() => controller.abort(), IDLE_TIMEOUT_MS)
  const extendDeadline = () => {
    clearTimeout(idleTimer)
    idleTimer = setTimeout(() => controller.abort(), IDLE_TIMEOUT_MS)
  }

  let sawEnd = false
  const dispatch = (data: string) => {
    const event = parseChatEvent(data)
    if (!event) return
    if (endsStream(event)) sawEnd = true
    onEvent(event)
  }

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(request),
      signal: controller.signal,
    })

    if (res.status === 429) return { kind: 'over_limit', message: await readFailureMessage(res) }
    if (!res.ok) return { kind: 'unavailable', message: await readFailureMessage(res) }
    if (!res.body) return { kind: 'network' }

    const reader = res.body.getReader()
    // stream: true keeps a multi-byte character intact across a chunk boundary.
    const decoder = new TextDecoder()
    const parser = createSseParser()

    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      extendDeadline()
      parser.push(decoder.decode(value, { stream: true })).forEach(dispatch)
    }
    parser.push(decoder.decode()).forEach(dispatch)
    parser.flush().forEach(dispatch)

    return sawEnd ? { kind: 'complete' } : { kind: 'network' }
  } catch {
    return sawEnd ? { kind: 'complete' } : { kind: 'network' }
  } finally {
    clearTimeout(idleTimer)
  }
}
