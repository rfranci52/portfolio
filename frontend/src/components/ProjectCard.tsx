import { Link } from 'react-router-dom'
import type { Project } from '../api'

interface Props {
  project: Project
  // h2 on the projects page; h3 on home, where the cards sit under the "Selected work" heading.
  heading?: 'h2' | 'h3'
}

export default function ProjectCard({ project, heading: Heading = 'h2' }: Props) {
  return (
    <Link
      to={`/projects/${project.slug}`}
      className="group block rounded-lg border border-border bg-surface p-5 transition-colors hover:border-accent/50"
    >
      <div className="flex items-center justify-between gap-4">
        <Heading className="font-medium text-fg transition-colors group-hover:text-accent">{project.title}</Heading>
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
