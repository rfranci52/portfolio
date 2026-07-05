import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getProject, type Project } from '../api'

export default function ProjectDetail() {
  const { slug = '' } = useParams()
  const [project, setProject] = useState<Project | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getProject(slug).then(setProject).catch((e: Error) => setError(e.message))
  }, [slug])

  if (error) return <p className="text-sm text-red-400">{error}</p>
  if (!project) return <p className="font-mono text-sm text-muted">loading…</p>

  return (
    <article>
      <Link to="/projects" className="font-mono text-sm text-muted hover:text-fg">← projects</Link>
      <h1 className="mt-6 text-3xl font-semibold tracking-tight text-fg">{project.title}</h1>
      <p className="mt-3 text-lg text-muted">{project.tagline}</p>

      <div className="mt-5 flex flex-wrap gap-2">
        {project.tech.map((t) => (
          <span key={t} className="rounded border border-border px-2 py-0.5 font-mono text-xs text-muted">{t}</span>
        ))}
      </div>

      {(project.repo_url || project.demo_url) && (
        <div className="mt-5 flex gap-4 font-mono text-sm">
          {project.demo_url && (
            <a href={project.demo_url} target="_blank" rel="noreferrer" className="text-accent hover:underline">live demo →</a>
          )}
          {project.repo_url && (
            <a href={project.repo_url} target="_blank" rel="noreferrer" className="text-muted hover:text-fg">source →</a>
          )}
        </div>
      )}

      <p className="mt-8 border-l-2 border-accent/40 pl-4 leading-relaxed text-fg">{project.summary}</p>

      {project.video_url && (
        <figure className="mt-8">
          <video
            src={project.video_url}
            controls
            playsInline
            preload="metadata"
            className="w-full rounded-lg border border-border"
          />
          <figcaption className="mt-2 font-mono text-xs text-muted">
            Recorded end to end: the automation driving the app (left) with its live log (right).
          </figcaption>
        </figure>
      )}

      {project.highlights.length > 0 && (
        <ul className="mt-8 space-y-2">
          {project.highlights.map((h, i) => (
            <li key={i} className="flex gap-3 text-muted">
              <span className="mt-2.5 h-1 w-1 shrink-0 rounded-full bg-accent" />
              <span>{h}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-12 space-y-10">
        {project.sections.map((s, i) => (
          <section key={i}>
            <h2 className="font-mono text-xs uppercase tracking-widest text-accent">{s.heading}</h2>
            <p className="mt-3 leading-relaxed text-muted">{s.body}</p>
          </section>
        ))}
      </div>
    </article>
  )
}
