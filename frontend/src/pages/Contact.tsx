import { useState, type ChangeEvent, type FormEvent } from 'react'
import { ContactError, sendContact } from '../api'
import { SITE } from '../config'
import { pageTitle, useDocumentTitle } from '../title'

type Status = 'idle' | 'sending' | 'sent' | 'error'

const EMPTY_FORM = { name: '', email: '', message: '', extra: '' }

export default function Contact() {
  useDocumentTitle(pageTitle('Contact'))
  const [form, setForm] = useState(EMPTY_FORM)
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
      setForm(EMPTY_FORM)
    } catch (error) {
      const message = error instanceof ContactError ? error.message : ''
      setFeedback(message || `Something went wrong sending that. Please email ${SITE.email} directly.`)
      setStatus('error')
    }
  }

  const field =
    'w-full rounded-md border border-border bg-surface px-3 py-2 text-fg placeholder:text-muted outline-none focus:border-accent'

  return (
    <div className="max-w-xl">
      <h1 className="text-3xl font-semibold tracking-tight text-fg">Contact</h1>
      <p className="mt-3 text-muted">
        Questions about any of this work? Send a note, or email{' '}
        <a href={`mailto:${SITE.email}`} className="text-accent hover:underline">{SITE.email}</a>.
      </p>

      {status === 'sent' ? (
        <p className="mt-8 rounded-md border border-accent/40 bg-accent/5 px-4 py-3 text-fg">{feedback}</p>
      ) : (
        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <input className={field} aria-label="Name" placeholder="Name" value={form.name} onChange={update('name')} maxLength={200} required />
          <input className={field} aria-label="Email" type="email" placeholder="Email" value={form.email} onChange={update('email')} maxLength={320} required />
          <textarea className={field} aria-label="Message" rows={5} placeholder="Message" value={form.message} onChange={update('message')} maxLength={5000} required />
          {/* Kept out of sight and out of the tab order, so a person never fills it in. */}
          <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
            <input name="extra" tabIndex={-1} autoComplete="off" value={form.extra} onChange={update('extra')} />
          </div>
          <button
            type="submit"
            disabled={status === 'sending'}
            className="rounded-md bg-accent px-5 py-2 font-medium text-bg transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {status === 'sending' ? 'Sending…' : 'Send'}
          </button>
          {status === 'error' && <p role="alert" className="text-sm text-red-400">{feedback}</p>}
        </form>
      )}
    </div>
  )
}
