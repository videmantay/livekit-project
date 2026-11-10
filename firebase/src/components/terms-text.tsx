import type { ReactNode } from 'react'

// Renders the small Markdown subset the terms use (headings, **bold**, _italic_),
// as React text nodes. Never injects HTML.
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|_[^_]+_)/g).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={i}>{part.slice(2, -2)}</strong>
    if (part.length > 2 && part.startsWith('_') && part.endsWith('_')) return <em key={i}>{part.slice(1, -1)}</em>
    return part
  })
}

export function TermsText({ text }: { text: string }) {
  const blocks = text.split(/\n\s*\n/).map((b) => b.trim()).filter(Boolean)
  return (
    <div className="flex flex-col gap-3 text-[15px]/relaxed text-body">
      {blocks.map((block, i) => {
        const heading = /^#{1,3}\s+(.*)$/.exec(block)
        if (heading) {
          return (
            <h2 key={i} className="text-xl font-semibold text-foreground">
              {heading[1]}
            </h2>
          )
        }
        return <p key={i}>{inline(block)}</p>
      })}
    </div>
  )
}
