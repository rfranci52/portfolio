import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useChat } from '../chat/context'
import ChatPanel from './ChatPanel'

const PHONE = '(max-width: 639px)'

/** The same conversation, docked at the bottom right of every page except home. */
export default function ChatWidget() {
  const { messages, busy } = useChat()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const [tucked, setTucked] = useState(false)

  // On a phone the open panel covers the page, so following a link closes it.
  useEffect(() => {
    if (window.matchMedia(PHONE).matches) setOpen(false)
    setTucked(false)
  }, [pathname])

  // On a phone the button floats over the text, so it steps aside while the reader
  // scrolls down and comes back on any scroll up or at the end of the page.
  useEffect(() => {
    const phone = window.matchMedia(PHONE)
    let last = window.scrollY
    function onScroll() {
      const y = window.scrollY
      const atEnd = window.innerHeight + y >= document.documentElement.scrollHeight - 8
      if (!phone.matches || atEnd || y < last - 8) {
        setTucked(false)
        last = y
      } else if (y > last + 8) {
        setTucked(true)
        last = y
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  if (open) {
    return (
      <div className="fixed bottom-4 right-4 z-40 h-[min(36rem,calc(100dvh-2rem))] w-[min(26rem,calc(100vw-2rem))]">
        <ChatPanel variant="dock" onClose={() => { setOpen(false); setTucked(false) }} />
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
      className={`fixed bottom-4 right-4 z-40 flex items-center gap-2 rounded-full bg-accent px-4 py-2.5 text-sm font-medium text-bg shadow-lg shadow-accent/20 ring-1 ring-accent/40 transition-all hover:brightness-105 hover:shadow-accent/40 motion-reduce:transition-none ${tucked ? 'translate-y-[calc(100%+2rem)] focus-visible:translate-y-0' : ''}`}
    >
      <span className="h-2 w-2 rounded-full bg-bg" />
      {text}
    </button>
  )
}
