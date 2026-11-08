import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useChat } from '../chat/context'
import ChatPanel from './ChatPanel'

/** The same conversation, docked at the bottom right of every page except home. */
export default function ChatWidget() {
  const { messages, busy } = useChat()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)

  // On a phone the open panel covers the page, so following a link closes it.
  useEffect(() => {
    if (window.matchMedia('(max-width: 639px)').matches) setOpen(false)
  }, [pathname])

  if (open) {
    return (
      <div className="fixed bottom-4 right-4 z-40 h-[min(36rem,calc(100dvh-2rem))] w-[min(26rem,calc(100vw-2rem))]">
        <ChatPanel variant="dock" onClose={() => setOpen(false)} />
      </div>
    )
  }

  let text = 'Ask about his work'
  if (messages.length > 0) text = 'Continue the conversation'
  if (busy) text = 'Answering…'

  return (
    <button
      type="button"
      onClick={() => setOpen(true)}
      className="fixed bottom-4 right-4 z-40 flex items-center gap-2 rounded-full bg-accent px-4 py-2.5 text-sm font-medium text-bg shadow-lg shadow-accent/20 ring-1 ring-accent/40 transition-all hover:brightness-105 hover:shadow-accent/40"
    >
      <span className="h-2 w-2 rounded-full bg-bg" />
      {text}
    </button>
  )
}
