import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getProjects, type Project } from '../api'
import { SITE } from '../config'
import ProjectCard from '../components/ProjectCard'

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([])
  useEffect(() => {
    getProjects().then(setProjects).catch(() => {})
  }, [])

  const featured = projects.filter((p) => p.featured)
  const shown = featured.length ? featured : projects.slice(0, 2)

  return (
    <div>
      <section>
        <p className="font-mono text-sm text-accent">{SITE.role}</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-fg sm:text-5xl">{SITE.name}</h1>
        <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">{SITE.intro}</p>

        <a
          href="https://demo.rakimfrancis.com"
          target="_blank"
          rel="noreferrer"
          className="group mt-8 flex max-w-xl items-center justify-between gap-4 rounded-xl bg-accent px-6 py-5 text-bg shadow-lg shadow-accent/20 ring-1 ring-accent/40 transition-all hover:brightness-105 hover:shadow-accent/40"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-bg/50"></span>
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-bg"></span>
              </span>
              <span className="font-mono text-xs font-semibold uppercase tracking-widest">Live demo</span>
            </div>
            <div className="mt-1.5 text-lg font-semibold leading-snug">Ask a database in plain English</div>
            <div className="text-sm text-bg/70">Type a question, watch it become SQL and answer live. Try it yourself.</div>
          </div>
          <span className="shrink-0 text-2xl transition-transform group-hover:translate-x-1">→</span>
        </a>

        <div className="mt-6 flex gap-5 font-mono text-sm">
          <Link to="/projects" className="text-accent hover:underline">view work →</Link>
          <Link to="/contact" className="text-muted hover:text-fg">get in touch</Link>
        </div>
      </section>

      <section className="mt-20">
        <h2 className="font-mono text-xs uppercase tracking-widest text-muted">Selected work</h2>
        <div className="mt-6 grid gap-4">
          {shown.map((p) => <ProjectCard key={p.slug} project={p} />)}
        </div>
      </section>
    </div>
  )
}
