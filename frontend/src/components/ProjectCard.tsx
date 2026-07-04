import { Link } from 'react-router-dom'
import type { Project } from '../api'

export default function ProjectCard({ project }: { project: Project }) {
  return (
    <Link
      to={`/projects/${project.slug}`}
      className="group block rounded-lg border border-border bg-surface p-5 transition-colors hover:border-accent/50"
    >
      <div className="flex items-center justify-between gap-4">
        <h3 className="font-medium text-fg transition-colors group-hover:text-accent">{project.title}</h3>
        {project.featured && <span className="font-mono text-xs text-accent">featured</span>}
      </div>
      <p className="mt-2 text-sm text-muted">{project.tagline}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {project.tech.slice(0, 5).map((t) => (
          <span key={t} className="rounded border border-border px-2 py-0.5 font-mono text-xs text-muted">{t}</span>
        ))}
      </div>
    </Link>
  )
}
