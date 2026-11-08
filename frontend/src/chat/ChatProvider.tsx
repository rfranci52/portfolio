import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { ChatContext, type ChatContextValue } from './context'
import { streamChat } from './sse'
import { getSessionId, getVisitorId, loadConversation, saveConversation } from './storage'
import { track } from './track'
import { MAX_QUESTION_CHARS, earlierTurns, finishTurn, newAssistantTurn, newId, reduceTurn } from './turn'
import type { ChatEvent, ChatMessage, FeedbackValue, WireMessage } from './types'

/** Holds the one conversation for the whole visit, above the routes. */
export default function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>(loadConversation)
  const [busy, setBusy] = useState(false)
  const latest = useRef(messages)
  const running = useRef(false)

  useEffect(() => {
    latest.current = messages
  }, [messages])

  // Saved between turns, not on every streamed token.
  useEffect(() => {
    if (!busy) saveConversation(messages)
  }, [messages, busy])

  const runTurn = useCallback(async (wire: WireMessage[], assistantId: string) => {
    running.current = true
    setBusy(true)
    const patch = (change: (turn: ChatMessage) => ChatMessage) =>
      setMessages((all) => all.map((m) => (m.id === assistantId ? change(m) : m)))

    const end = await streamChat(
      {
        messages: wire,
        session_id: getSessionId(),
        visitor_id: getVisitorId(),
        page: window.location.pathname,
        referrer: document.referrer,
      },
      (event: ChatEvent) => patch((turn) => reduceTurn(turn, event)),
    )

    patch((turn) => finishTurn(turn, end))
    running.current = false
    setBusy(false)
  }, [])

  const send = useCallback(
    (raw: string) => {
      const content = raw.trim().slice(0, MAX_QUESTION_CHARS)
      if (!content || running.current) return
      const earlier = earlierTurns(latest.current)
      const turn = newAssistantTurn()
      setMessages((all) => [...all, { id: newId(), role: 'user', content }, turn])
      void runTurn([...earlier, { role: 'user', content }], turn.id)
    },
    [runTurn],
  )

  const retry = useCallback(
    (assistantId: string) => {
      if (running.current) return
      const all = latest.current
      const index = all.findIndex((m) => m.id === assistantId)
      const question = all[index - 1]
      if (index < 1 || question.role !== 'user') return
      const earlier = earlierTurns(all.slice(0, index - 1))
      const turn = newAssistantTurn()
      setMessages((current) => current.map((m) => (m.id === assistantId ? turn : m)))
      void runTurn([...earlier, { role: 'user', content: question.content }], turn.id)
    },
    [runTurn],
  )

  const clear = useCallback(() => {
    if (!running.current) setMessages([])
  }, [])

  const rate = useCallback((assistantId: string, value: FeedbackValue) => {
    const turn = latest.current.find((m) => m.id === assistantId)
    if (!turn?.turnId || turn.feedback === value) return
    setMessages((all) => all.map((m) => (m.id === assistantId ? { ...m, feedback: value } : m)))
    track('feedback', { turn_id: turn.turnId, data: { value } })
  }, [])

  const value = useMemo<ChatContextValue>(
    () => ({ messages, busy, send, retry, clear, rate }),
    [messages, busy, send, retry, clear, rate],
  )

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}
