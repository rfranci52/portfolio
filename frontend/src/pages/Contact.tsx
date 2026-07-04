import { useState, type ChangeEvent, type FormEvent } from 'react'
import { sendContact } from '../api'
import { SITE } from '../config'

type Status = 'idle' | 'sending' | 'sent' | 'error'

export default function Contact() {
  const [form, setForm] = useState({ name: '', email: '', message: '' })
  const [status, setStatus] = useState<Status>('idle')
  const [feedback, setFeedback] = useState('')

  const update =
    (key: keyof typeof form) =>
    (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm({ ...form, [key]: e.target.value })

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setStatus('sending')
    try {
      const res = await sendContact(form)
      setFeedback(res.message)
      setStatus('sent')
      setForm({ name: '', email: '', message: '' })
    } catch {
      setFeedback('Something went wrong sending that. Email me directly?')
      setStatus('error')
    }
  }

  const field =
    'w-full rounded-md border border-border bg-surface px-3 py-2 text-fg placeholder:text-muted outline-none focus:border-accent'

  return (
    <div className="max-w-xl">
      <h1 className="text-3xl font-semibold tracking-tight text-fg">Contact</h1>
      <p className="mt-3 text-muted">
        Have a role or a project in mind? Send a note — or email{' '}
        <a href={`mailto:${SITE.email}`} className="text-accent hover:underline">{SITE.email}</a>.
      </p>

      {status === 'sent' ? (
        <p className="mt-8 rounded-md border border-accent/40 bg-accent/5 px-4 py-3 text-fg">{feedback}</p>
      ) : (
        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <input className={field} placeholder="Name" value={form.name} onChange={update('name')} required />
          <input className={field} type="email" placeholder="Email" value={form.email} onChange={update('email')} required />
          <textarea className={field} rows={5} placeholder="Message" value={form.message} onChange={update('message')} required />
          <button
            type="submit"
            disabled={status === 'sending'}
            className="rounded-md bg-accent px-5 py-2 font-medium text-bg transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {status === 'sending' ? 'Sending…' : 'Send'}
          </button>
          {status === 'error' && <p className="text-sm text-red-400">{feedback}</p>}
        </form>
      )}
    </div>
  )
}
