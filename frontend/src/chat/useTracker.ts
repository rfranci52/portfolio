import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { takeSessionStart } from './storage'
import { track } from './track'

const DEPTHS = [25, 50, 75, 100]
const MAX_LABEL_CHARS = 80

/** Records pageviews on route change, scroll depth per page, and clicks on links and buttons. */
export function useTracker(): void {
  const { pathname } = useLocation()
  const lastPath = useRef<string | null>(null)
  const reached = useRef(new Set<number>())

  useEffect(() => {
    if (lastPath.current === pathname) return
    lastPath.current = pathname
    reached.current = new Set()
    if (takeSessionStart()) track('session_start', { referrer: document.referrer })
    track('pageview', { referrer: document.referrer })
  }, [pathname])

  useEffect(() => {
    let frame = 0

    const measure = () => {
      frame = 0
      const page = document.documentElement
      const scrollable = page.scrollHeight - window.innerHeight
      if (scrollable <= 0) return
      const percent = (window.scrollY / scrollable) * 100
      for (const depth of DEPTHS) {
        if (percent + 0.5 >= depth && !reached.current.has(depth)) {
          reached.current.add(depth)
          track('scroll', { data: { depth } })
        }
      }
    }

    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(measure)
    }

    // Capture runs before a link click changes the route, so the path is still the page clicked on.
    const onClick = (event: MouseEvent) => {
      if (!(event.target instanceof Element)) return
      const control = event.target.closest('a, button')
      if (!control) return
      const label = (control.getAttribute('aria-label') ?? control.textContent ?? '').trim()
      track('click', {
        data: {
          tag: control.tagName.toLowerCase(),
          text: label.slice(0, MAX_LABEL_CHARS),
          href: control.getAttribute('href') ?? undefined,
        },
      })
    }

    window.addEventListener('scroll', onScroll, { passive: true })
    document.addEventListener('click', onClick, true)
    return () => {
      window.removeEventListener('scroll', onScroll)
      document.removeEventListener('click', onClick, true)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [])
}
