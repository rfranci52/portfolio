import { Link } from 'react-router-dom'
import { pageTitle, useDocumentTitle } from '../title'

/** Shown for any address the site doesn't have, including an unknown project. */
export default function NotFound() {
  useDocumentTitle(pageTitle('Page not found'))

  return (
    <div>
      <h1 className="text-3xl font-semibold tracking-tight text-fg">Page not found</h1>
      <p className="mt-3 text-muted">That address isn't on this site.</p>
      <div className="mt-5 flex gap-5 font-mono text-sm">
        <Link to="/" className="inline-block py-1 text-accent hover:underline">home →</Link>
        <Link to="/projects" className="inline-block py-1 text-muted hover:text-fg">projects →</Link>
      </div>
    </div>
  )
}
