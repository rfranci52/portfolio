export type Stage = 'searching' | 'looking_up' | 'writing'

export interface Passage {
  id: string
  title: string
  section: string
  url: string
  snippet: string
}

export interface WorkSource {
  title: string
  section: string
  url: string
}

export interface WebSource {
  title: string
  url: string
}

export interface Sources {
  work: WorkSource[]
  web: WebSource[]
}

export interface RelatedLink {
  title: string
  url: string
}

// The events /api/chat sends, after validation in sse.ts.
export type ChatEvent =
  | { type: 'status'; stage: Stage }
  | { type: 'passages'; items: Passage[] }
  | { type: 'lookup' }
  | { type: 'delta'; text: string }
  | { type: 'retract'; text: string }
  | { type: 'error'; message: string; code: string }
  | {
      type: 'done'
      turnId: string
      model: string
      costUsd: number | null
      ms: number | null
      cited: string[]
      sources: Sources
      related: RelatedLink[]
      signature: string
    }

// How a request ended, separate from what the server said inside the stream.
export type StreamEnd =
  | { kind: 'complete' }
  | { kind: 'over_limit'; message: string }
  | { kind: 'unavailable'; message: string }
  | { kind: 'network' }

export type TurnState = 'streaming' | 'done' | 'over_limit' | 'error' | 'network'

export type FeedbackValue = 'up' | 'down'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  state?: TurnState
  stage?: Stage
  passages?: Passage[]
  notice?: string
  turnId?: string
  model?: string
  costUsd?: number | null
  ms?: number | null
  cited?: string[]
  sources?: Sources
  related?: RelatedLink[]
  signature?: string
  feedback?: FeedbackValue
}

export interface WireMessage {
  role: 'user' | 'assistant'
  content: string
  signature?: string
}

export interface ChatRequest {
  messages: WireMessage[]
  session_id: string
  visitor_id: string
  page: string
  referrer: string
}
