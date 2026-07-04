import { SITE } from '../config'

export default function About() {
  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl font-semibold tracking-tight text-fg">About</h1>
      <div className="mt-6 space-y-4 leading-relaxed text-muted">
        {SITE.about.map((para, i) => <p key={i}>{para}</p>)}
      </div>
    </div>
  )
}
