import { useEffect } from 'react'
import { SITE } from './config'

// The home page keeps the full title that index.html starts with.
export const HOME_TITLE = `${SITE.name} · Software Engineer · Automation & AI`

/** A page's tab title, for example "Projects · Rakim Francis". */
export function pageTitle(name: string): string {
  return `${name} · ${SITE.name}`
}

/** Sets the browser tab title. Undefined leaves it alone while a page is still loading. */
export function useDocumentTitle(title: string | undefined): void {
  useEffect(() => {
    if (title) document.title = title
  }, [title])
}
