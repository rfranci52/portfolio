const SITE_HOSTS = new Set(['rakimfrancis.com', 'www.rakimfrancis.com'])
const DEMO_HOST = 'demo.rakimfrancis.com'

export type SafeLink = { kind: 'internal'; to: string } | { kind: 'external'; href: string }

/** Allowlist for links in answers: this site and the live demo, nothing else. */
export function classifySiteLink(url: string): SafeLink | null {
  const value = url.trim()
  if (value.startsWith('/')) {
    // "//host" and "/\host" are treated by browsers as other origins.
    if (value.startsWith('//') || value.includes('\\')) return null
    return { kind: 'internal', to: value }
  }
  let parsed: URL
  try {
    parsed = new URL(value)
  } catch {
    return null
  }
  if (parsed.protocol !== 'https:' || parsed.username || parsed.password) return null
  if (SITE_HOSTS.has(parsed.hostname)) {
    // A router treats a path starting "//" as another site.
    if (parsed.pathname.startsWith('//')) return null
    return { kind: 'internal', to: `${parsed.pathname}${parsed.search}${parsed.hash}` }
  }
  if (parsed.hostname === DEMO_HOST) return { kind: 'external', href: parsed.href }
  return null
}

/** Web sources may point anywhere public, but only over http or https. */
export function webHref(url: string): string | null {
  try {
    const parsed = new URL(url.trim())
    return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? parsed.href : null
  } catch {
    return null
  }
}
