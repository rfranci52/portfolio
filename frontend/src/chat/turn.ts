import type { ChatEvent, ChatMessage, StreamEnd, WireMessage } from './types'

export const MAX_QUESTION_CHARS = 800

// Earlier turns sent with a question, always whole question and answer pairs.
const MAX_EARLIER_MESSAGES = 6

// The server keeps this many characters of earlier turns, so sending more is wasted.
const MAX_EARLIER_CHARS = 2000

const OVER_LIMIT = /over.?limit|quota|rate.?limit|daily limit/i

export function newId(): string {
  try {
    return crypto.randomUUID()
  } catch {
    // randomUUID only exists on secure origins.
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
  }
}

export function newAssistantTurn(): ChatMessage {
  return { id: newId(), role: 'assistant', content: '', state: 'streaming', stage: 'searching' }
}

/** Folds one server event into an assistant turn. Pure, so it can run during a React update. */
export function reduceTurn(turn: ChatMessage, event: ChatEvent): ChatMessage {
  switch (event.type) {
    case 'status':
      return turn.state === 'streaming' ? { ...turn, stage: event.stage } : turn
    case 'passages':
      return turn.state === 'streaming' ? { ...turn, passages: event.items } : turn
    case 'lookup':
      return turn.state === 'streaming' ? { ...turn, stage: 'looking_up' } : turn
    case 'delta':
      if (turn.state !== 'streaming') return turn
      return { ...turn, content: turn.content + event.text, stage: 'writing' }
    case 'retract':
      // Replaces whatever was showing. The turn stays open until the done event.
      if (turn.state !== 'streaming') return turn
      return { ...turn, content: event.text }
    case 'error':
      return {
        ...turn,
        state: OVER_LIMIT.test(`${event.code} ${event.message}`) ? 'over_limit' : 'error',
        stage: undefined,
        notice: event.message,
      }
    case 'done':
      if (turn.state !== 'streaming') return turn
      return {
        ...turn,
        state: 'done',
        stage: undefined,
        turnId: event.turnId,
        model: event.model,
        costUsd: event.costUsd,
        ms: event.ms,
        cited: event.cited,
        sources: event.sources,
        related: event.related,
        signature: event.signature,
      }
  }
}

/** Settles a turn once the request is over. */
export function finishTurn(turn: ChatMessage, end: StreamEnd): ChatMessage {
  if (turn.state !== 'streaming') return turn
  switch (end.kind) {
    case 'complete':
      return { ...turn, state: 'done', stage: undefined }
    case 'over_limit':
      return { ...turn, state: 'over_limit', stage: undefined, notice: end.message }
    case 'unavailable':
      return { ...turn, state: 'error', stage: undefined, notice: end.message }
    case 'network':
      return { ...turn, state: 'network', stage: undefined }
  }
}

/** An answer as plain words, for the screen reader announcement. */
export function plainAnswer(markdown: string): string {
  return markdown.replace(/\*\*(.+?)\*\*/g, '$1').replace(/\[([^\]\n]+)\]\([^)\s]+\)/g, '$1')
}

/**
 * Earlier turns worth sending: only finished question and answer pairs, newest
 * first until the server's budget is covered. An answer goes back whole, because
 * its signature covers the whole text. The server does the final trimming.
 */
export function earlierTurns(messages: ChatMessage[]): WireMessage[] {
  const pairs: WireMessage[] = []
  let chars = 0
  for (let i = messages.length - 2; i >= 0 && chars < MAX_EARLIER_CHARS; i -= 1) {
    const question = messages[i]
    const answer = messages[i + 1]
    if (question.role === 'user' && answer.role === 'assistant' && answer.state === 'done' && answer.content && answer.signature) {
      pairs.unshift(
        { role: 'user', content: question.content },
        { role: 'assistant', content: answer.content, signature: answer.signature },
      )
      chars += question.content.length + answer.content.length
    }
  }
  return pairs.slice(-MAX_EARLIER_MESSAGES)
}
