export interface ProjectSection {
  heading: string
  body: string
}

export interface Project {
  id: number
  slug: string
  title: string
  tagline: string
  summary: string
  tech: string[]
  highlights: string[]
  sections: ProjectSection[]
  repo_url: string | null
  demo_url: string | null
  video_url: string | null
  featured: boolean
  sort_order: number
  created_at: string
}

export interface ContactPayload {
  name: string
  email: string
  message: string
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(detail || `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export const getProjects = () => fetch('/api/projects').then(json<Project[]>)

export const getProject = (slug: string) =>
  fetch(`/api/projects/${slug}`).then(json<Project>)

export const sendContact = (payload: ContactPayload) =>
  fetch('/api/contact', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).then(json<{ ok: boolean; message: string }>)
