import projectsData from './projects.json'

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
  // Hidden on the page, so a person leaves it empty.
  extra: string
}

/** The server refused a message and said what the sender should do instead. */
export class ContactError extends Error {}

// Projects are baked in at build time; instant loads, no backend needed.
const PROJECTS = (projectsData as unknown as Project[])
  .slice()
  .sort((a, b) => a.sort_order - b.sort_order)

export const getProjects = async (): Promise<Project[]> => PROJECTS

export const getProject = async (slug: string): Promise<Project> => {
  const project = PROJECTS.find((p) => p.slug === slug)
  if (!project) throw new Error('Project not found')
  return project
}

export async function sendContact(payload: ContactPayload): Promise<{ ok: boolean; message: string }> {
  const res = await fetch('/api/contact', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const body = (await res.json().catch(() => null)) as { ok?: boolean; message?: string } | null
  if (!res.ok || !body?.ok) throw new ContactError(body?.message ?? '')
  return { ok: true, message: body.message ?? '' }
}
