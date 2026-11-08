import { getSessionId, getVisitorId } from './storage'

export type TrackKind = 'pageview' | 'scroll' | 'click' | 'session_start' | 'feedback'

interface TrackFields {
  turn_id?: string
  referrer?: string
  data?: Record<string, unknown>
}

// The endpoint rejects bodies over 4 KB.
const MAX_BODY_CHARS = 3800

export function track(kind: TrackKind, fields: TrackFields = {}): void {
  const body = JSON.stringify({
    kind,
    visitor_id: getVisitorId(),
    session_id: getSessionId(),
    path: window.location.pathname,
    ...fields,
  })
  if (body.length > MAX_BODY_CHARS) return

  try {
    const blob = new Blob([body], { type: 'application/json' })
    if (navigator.sendBeacon?.('/api/track', blob)) return
  } catch {
    // Fall through to fetch.
  }
  fetch('/api/track', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    keepalive: true,
  }).catch(() => {
    // Measurement must never surface to a visitor.
  })
}
