import { useEffect, useState } from 'react'
import { getProjects, type Project } from '../api'
import ProjectCard from '../components/ProjectCard'

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([])
  const [error, setError] = useState('')
  useEffect(() => {
    getProjects().then(setProjects).catch((e: Error) => setError(e.message))
  }, [])

  return (
    <div>
      <h1 className="text-3xl font-semibold tracking-tight text-fg">Projects</h1>
      <p className="mt-3 text-muted">Things I've designed and built.</p>
      {error && <p className="mt-6 text-sm text-red-400">Couldn't load projects: {error}</p>}
      <div className="mt-8 grid gap-4">
        {projects.map((p) => <ProjectCard key={p.slug} project={p} />)}
      </div>
    </div>
  )
}
