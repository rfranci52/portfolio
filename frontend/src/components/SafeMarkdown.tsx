import type { ReactNode } from 'react'
import SiteLink from './SiteLink'

// A deliberately small subset: bold, bullet and numbered lists, and links on
// the allowlist. Output is React text and elements only, so model text can
// never become markup.

type ListBlock = { kind: 'ul' | 'ol'; items: string[] }
type Block = { kind: 'p'; text: string } | ListBlock

function parseBlocks(source: string): Block[] {
  const blocks: Block[] = []
  let paragraph: string[] = []
  let list = null as ListBlock | null

  const endParagraph = () => {
    if (paragraph.length > 0) blocks.push({ kind: 'p', text: paragraph.join(' ') })
    paragraph = []
  }
  const endList = () => {
    if (list) blocks.push(list)
    list = null
  }

  for (const raw of source.split('\n')) {
    const line = raw.trim()
    if (line === '') {
      endParagraph()
      endList()
      continue
    }
    const bullet = /^[-*+]\s+(.*)$/.exec(line)
    const numbered = /^\d+[.)]\s+(.*)$/.exec(line)
    const item = bullet ?? numbered
    if (item) {
      const kind = bullet ? 'ul' : 'ol'
      endParagraph()
      if (list?.kind !== kind) endList()
      list ??= { kind, items: [] }
      list.items.push(item[1])
    } else {
      endList()
      paragraph.push(line.replace(/^#{1,6}\s+/, ''))
    }
  }
  endParagraph()
  endList()
  return blocks
}

const INLINE = /\*\*(.+?)\*\*|\[([^\]\n]+)\]\(([^)\s]+)\)/g

function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = []
  let cursor = 0
  for (const match of text.matchAll(INLINE)) {
    if (match.index > cursor) nodes.push(text.slice(cursor, match.index))
    if (match[1] !== undefined) {
      nodes.push(<strong key={match.index} className="font-semibold text-fg">{renderInline(match[1])}</strong>)
    } else {
      nodes.push(
        <SiteLink key={match.index} url={match[3]} className="text-accent hover:underline">
          {match[2]}
        </SiteLink>,
      )
    }
    cursor = match.index + match[0].length
  }
  if (cursor < text.length) nodes.push(text.slice(cursor))
  return nodes
}

/** While text is streaming, hides a half-written bold marker or link at the end. */
function hideUnfinishedMarkup(source: string): string {
  const lineStart = source.lastIndexOf('\n') + 1
  let tail = source.slice(lineStart)
  tail = tail.replace(/\[[^\]]*(\]\([^)]*)?$/, '')
  tail = tail.replace(/(^|[^*])\*$/, '$1')
  if ((tail.split('**').length - 1) % 2 === 1) {
    const marker = tail.lastIndexOf('**')
    tail = tail.slice(0, marker) + tail.slice(marker + 2)
  }
  return source.slice(0, lineStart) + tail
}

export default function SafeMarkdown({ text, streaming = false }: { text: string; streaming?: boolean }) {
  const blocks = parseBlocks(streaming ? hideUnfinishedMarkup(text) : text)
  return (
    <div className="space-y-3 text-[15px] leading-relaxed text-fg">
      {blocks.map((block, i) => {
        if (block.kind === 'p') return <p key={i} className="break-words">{renderInline(block.text)}</p>
        const List = block.kind
        return (
          <List key={i} className={`space-y-1 pl-5 ${block.kind === 'ul' ? 'list-disc' : 'list-decimal'}`}>
            {block.items.map((item, j) => <li key={j} className="break-words">{renderInline(item)}</li>)}
          </List>
        )
      })}
    </div>
  )
}
