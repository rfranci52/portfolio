export interface EvalCategory {
  name: string
  passed: number
  total: number
}

export interface EvalResults {
  date: string
  model: string
  effort: string
  categories: EvalCategory[]
  medianMs: number
  medianCostUsd: number
}

const isCount = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value) && value >= 0

function readCategory(value: unknown): EvalCategory | null {
  if (typeof value !== 'object' || value === null) return null
  const { name, passed, total } = value as Record<string, unknown>
  if (typeof name !== 'string' || !isCount(passed) || !isCount(total) || total === 0 || passed > total) return null
  return { name, passed, total }
}

/**
 * Reads the published evaluation numbers. Returns null unless the file holds a
 * complete, finished run, so the page can never show a partial or made-up figure.
 */
export function readEvalResults(raw: unknown): EvalResults | null {
  if (typeof raw !== 'object' || raw === null) return null
  const summary = raw as Record<string, unknown>
  if (summary.status !== 'ok' || !Array.isArray(summary.categories)) return null
  if (typeof summary.date !== 'string' || typeof summary.model !== 'string' || typeof summary.effort !== 'string') return null
  if (!isCount(summary.median_ms) || !isCount(summary.median_cost_usd)) return null

  const categories = summary.categories.map(readCategory)
  if (categories.length === 0 || categories.includes(null)) return null

  return {
    date: summary.date,
    model: summary.model,
    effort: summary.effort,
    categories: categories as EvalCategory[],
    medianMs: summary.median_ms,
    medianCostUsd: summary.median_cost_usd,
  }
}
