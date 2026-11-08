import { newId } from './turn'
import type { ChatMessage } from './types'

type Area = 'localStorage' | 'sessionStorage'

// Storage can throw or be missing in private windows and with site data blocked.
// Everything here still works for the life of the page when that happens.
function read(area: Area, key: string): string | null {
  try {
    return window[area].getItem(key)
  } catch {
    return null
  }
}

function write(area: Area, key: string, value: string): void {
  try {
    window[area].setItem(key, value)
  } catch {
    // Nothing to do: the value stays in memory for this page load.
  }
}

function remove(area: Area, key: string): void {
  try {
    window[area].removeItem(key)
  } catch {
    // Nothing to do.
  }
}

const VISITOR_KEY = 'site.visitor_id'
const SESSION_KEY = 'site.session_id'
const CONVERSATION_KEY = 'site.conversation'
const MAX_STORED_MESSAGES = 40

let visitorId: string | null = null
let sessionId: string | null = null
let sessionIsNew = false

export function getVisitorId(): string {
  visitorId ??= read('localStorage', VISITOR_KEY)
  if (!visitorId) {
    visitorId = newId()
    write('localStorage', VISITOR_KEY, visitorId)
  }
  return visitorId
}

export function getSessionId(): string {
  sessionId ??= read('sessionStorage', SESSION_KEY)
  if (!sessionId) {
    sessionId = newId()
    sessionIsNew = true
    write('sessionStorage', SESSION_KEY, sessionId)
  }
  return sessionId
}

/** True once, for the page load that created this session. */
export function takeSessionStart(): boolean {
  getSessionId()
  const started = sessionIsNew
  sessionIsNew = false
  return started
}

function isStoredMessage(value: unknown): value is ChatMessage {
  if (typeof value !== 'object' || value === null) return false
  const message = value as Partial<ChatMessage>
  return (
    typeof message.id === 'string' &&
    typeof message.content === 'string' &&
    (message.role === 'user' || message.role === 'assistant')
  )
}

export function loadConversation(): ChatMessage[] {
  const stored = read('sessionStorage', CONVERSATION_KEY)
  if (!stored) return []
  try {
    const parsed: unknown = JSON.parse(stored)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(isStoredMessage)
  } catch {
    return []
  }
}

export function saveConversation(messages: ChatMessage[]): void {
  if (messages.length === 0) {
    remove('sessionStorage', CONVERSATION_KEY)
    return
  }
  write('sessionStorage', CONVERSATION_KEY, JSON.stringify(messages.slice(-MAX_STORED_MESSAGES)))
}
