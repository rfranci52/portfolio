import { Link } from 'react-router-dom'
import { pageTitle, useDocumentTitle } from '../title'

const GROUPS = [
  {
    title: 'Every page visit',
    items: [
      'The page and the address you came from, if your browser shares it.',
      'How far down the page you scrolled, in steps of a quarter.',
      'Which links and buttons you clicked, with their label and destination.',
      'A random visitor ID kept in your browser, and a session ID that lasts until the tab closes. These connect visits to each other.',
      'Internet protocol (IP) address, approximate location (city, region and country) and browser details, including whether the device is a desktop, phone or tablet.',
    ],
  },
  {
    title: 'If you use the chat',
    items: [
      'Your questions and the answers, along with the visitor and session IDs and the visit details above.',
      'How each answer was produced: the passages and public lookups it used, the model, its cost and its timing.',
      'A thumbs up or down, if you give one.',
      'Your questions also go to the language model and search services that produce the answer.',
    ],
  },
  {
    title: 'If you use the contact form',
    items: [
      'Your name, email address and message. They are saved and sent to Rakim through an email delivery service.',
    ],
  },
  {
    title: 'Limits',
    items: [
      'A count against your IP address for the day, so that one visitor cannot use up the chat or the contact form.',
    ],
  },
  {
    title: 'Kept in your browser',
    items: [
      "The visitor ID, until you clear this site's data. The session ID and the current chat, until the tab closes.",
    ],
  },
]

export default function WhatIsSaved() {
  useDocumentTitle(pageTitle('What is saved'))
  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl font-semibold tracking-tight text-fg">What is saved</h1>
      <p className="mt-3 leading-relaxed text-muted">
        This site records how it is used so it can improve. This page lists what it keeps. Page
        views are also counted by the hosting provider's web analytics.
      </p>

      <div className="mt-10 space-y-8">
        {GROUPS.map((group) => (
          <section key={group.title}>
            <h2 className="font-mono text-xs uppercase tracking-widest text-accent">{group.title}</h2>
            <ul className="mt-3 list-disc space-y-1.5 pl-5 leading-relaxed text-muted">
              {group.items.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </section>
        ))}
      </div>

      <p className="mt-10 leading-relaxed text-muted">
        Questions about any of this can go through the{' '}
        <Link to="/contact" className="text-accent hover:underline">contact page</Link>.
      </p>
    </div>
  )
}
