import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { classifySiteLink } from '../chat/links'

interface Props {
  url: string
  className?: string
  children: ReactNode
}

/** A link to this site or the live demo. Any other address renders as plain text. */
export default function SiteLink({ url, className, children }: Props) {
  const link = classifySiteLink(url)
  if (!link) return <>{children}</>
  if (link.kind === 'internal') {
    return <Link to={link.to} className={className}>{children}</Link>
  }
  return <a href={link.href} target="_blank" rel="noreferrer" className={className}>{children}</a>
}
