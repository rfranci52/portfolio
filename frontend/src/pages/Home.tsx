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
