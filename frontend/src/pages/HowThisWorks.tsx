import { readEvalResults, type EvalResults } from '../chat/evalSummary'
import rawSummary from '../eval_summary.json'

const PIPELINE = [
  {
    title: 'Limits',
    body: 'Each visitor gets a fixed number of questions per day, and the whole site has a daily cap on questions and on model spending. Only questions that reach the model count. If a limit check cannot run, the chat stays closed rather than spending without a meter.',
  },
  {
    title: 'Privacy screen on the question',
    body: 'The question is checked before anything else reads it. Some questions stop here and get one fixed reply, with no model call at all.',
  },
  {
    title: 'Retrieval',
    body: 'Two searches run side by side over his written case studies: one by meaning, using vector embeddings, and one by exact words, using Postgres full-text search. Reciprocal rank fusion merges the two lists and the top eight passages move on. No model writes a database query at any point.',
  },
  {
    title: 'Public lookups and organization context',
    body: 'While the passages are being found, a small model reads the screened question and reports at most one company, technology or industry that needs public information. Code runs that one lookup, so the model writing the answer cannot start a search. The search sees only the kind and the name, so the visitor\'s words never reach it. Every company takes the same path, results are cached, and the summary helps the answer point to his closest work.',
  },
  {
    title: 'Writing the answer',
    body: 'Claude writes from those passages, with citations back to them, in one streaming call with no tools. Claims about Rakim have to come from a passage. If the passages do not cover something, the answer says it is not in the record.',
  },
  {
    title: 'Screening the answer',
    body: 'The answer streams to the page as it is written, a few words behind the model, because the last few words are held back until they have been checked. If something trips the privacy screen, what was showing is replaced by a general reply. Links survive only if they point to this site or the live demo.',
  },
  {
    title: 'Measuring it',
    body: 'Answers show the model, cost and response time beneath them. Each turn is recorded with the passages it cited, so quality can be checked rather than assumed.',
  },
]

const PROTECTIONS = [
  {
    title: 'Rules that text cannot change',
    body: 'Words from visitors, passages and web lookups are handled as data. Nothing inside them can rewrite what the system is allowed to do.',
  },
  {
    title: 'Least-privilege database access',
    body: 'The part that answers questions can read the published passages and call a few fixed functions, and nothing else. The part that saves records can only add them and cannot read them back.',
  },
  {
    title: 'Nothing private in the source code',
    body: 'The privacy screen compares salted hashes kept in the database, so the public code contains nothing for it to give away.',
  },
  {
    title: 'What is saved',
    body: 'Questions, answers and basic visit details, including internet protocol (IP) address and approximate location, are saved so this site can improve.',
  },
]

function formatDuration(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} seconds` : `${Math.round(ms)} milliseconds`
}

function EvalNumbers({ results }: { results: EvalResults }) {
  return (
    <div className="mt-4">
      <p className="font-mono text-xs text-muted">
        {results.date} · {results.model} · effort {results.effort}
      </p>
      <div className="mt-4 overflow-hidden rounded-lg border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th scope="col" className="px-4 py-2 text-left font-mono text-xs font-normal uppercase tracking-widest text-muted">Category</th>
              <th scope="col" className="px-4 py-2 text-right font-mono text-xs font-normal uppercase tracking-widest text-muted">Passed</th>
            </tr>
          </thead>
          <tbody>
            {results.categories.map((category) => (
              <tr key={category.name} className="border-b border-border last:border-b-0">
                <td className="px-4 py-2 text-fg">{category.name}</td>
                <td className={`px-4 py-2 text-right font-mono ${category.passed === category.total ? 'text-accent' : 'text-fg'}`}>
                  {category.passed}/{category.total}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <dl className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <dt className="font-mono text-xs uppercase tracking-widest text-muted">Median response time</dt>
          <dd className="mt-1 text-lg text-fg">{formatDuration(results.medianMs)}</dd>
        </div>
        <div>
          <dt className="font-mono text-xs uppercase tracking-widest text-muted">Median cost per answer</dt>
          <dd className="mt-1 text-lg text-fg">${results.medianCostUsd.toFixed(4)}</dd>
        </div>
      </dl>
    </div>
  )
}

export default function HowThisWorks() {
  const results = readEvalResults(rawSummary)

  return (
    <div>
      <h1 className="text-3xl font-semibold tracking-tight text-fg">How this works</h1>
      <p className="mt-3 max-w-2xl leading-relaxed text-muted">
        The chat on this site answers from Rakim's written case studies, shows where each answer
        came from, and reports what it cost. This page explains the path a question takes, what
        protects it, and how it is tested.
      </p>

      <section className="mt-12">
        <h2 className="font-mono text-xs uppercase tracking-widest text-accent">The path of a question</h2>
        <ol className="mt-5 space-y-5">
          {PIPELINE.map((step, i) => (
            <li key={step.title} className="flex gap-4">
              <span className="w-5 shrink-0 pt-0.5 text-right font-mono text-sm text-accent">{i + 1}</span>
              <div className="min-w-0">
                <h3 className="font-medium text-fg">{step.title}</h3>
                <p className="mt-1 leading-relaxed text-muted">{step.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-12">
        <h2 className="font-mono text-xs uppercase tracking-widest text-accent">Protections</h2>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          {PROTECTIONS.map((item) => (
            <div key={item.title} className="rounded-lg border border-border bg-surface p-5">
              <h3 className="font-medium text-fg">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12">
        <h2 className="font-mono text-xs uppercase tracking-widest text-accent">Evaluation</h2>
        <p className="mt-3 leading-relaxed text-muted">
          A fixed set of test questions runs against the real pipeline. Exact checks come first,
          then a separate language model judges whether each answer stayed within its sources.
        </p>
        {results ? (
          <EvalNumbers results={results} />
        ) : (
          <p className="mt-4 rounded-md border border-border bg-surface px-4 py-3 text-sm text-fg">
            The test cases and their results are kept private, so this page shows no numbers.
          </p>
        )}
      </section>

      <section className="mt-12">
        <h2 className="font-mono text-xs uppercase tracking-widest text-accent">How it was built</h2>
        <p className="mt-3 leading-relaxed text-muted">
          Built with artificial intelligence (AI) assistance. The architecture, the rules it
          follows and the judgment calls behind them are Rakim's.
        </p>
      </section>
    </div>
  )
}
