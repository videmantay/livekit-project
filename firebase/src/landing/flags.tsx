import type { Locale } from './content'

// Inline SVGs, because flag emoji show as plain letters on Windows.
// Simplified at 3:2 so they stay readable at header size.

function UsFlag() {
  const stripes = Array.from({ length: 13 }, (_, i) => i).filter((i) => i % 2 === 0)
  return (
    <svg viewBox="0 0 30 20" aria-hidden className="size-full">
      <rect width="30" height="20" fill="#fff" />
      {stripes.map((i) => (
        <rect key={i} y={(i * 20) / 13} width="30" height={20 / 13} fill="#B22234" />
      ))}
      <rect width="12" height={(20 / 13) * 7} fill="#3C3B6E" />
    </svg>
  )
}

function MxFlag() {
  return (
    <svg viewBox="0 0 30 20" aria-hidden className="size-full">
      <rect width="10" height="20" fill="#006847" />
      <rect x="10" width="10" height="20" fill="#fff" />
      <rect x="20" width="10" height="20" fill="#CE1126" />
      <circle cx="15" cy="10" r="3" fill="#8C5A2B" />
    </svg>
  )
}

function BrFlag() {
  return (
    <svg viewBox="0 0 30 20" aria-hidden className="size-full">
      <rect width="30" height="20" fill="#009C3B" />
      <path d="M15 2.5 27 10 15 17.5 3 10Z" fill="#FFDF00" />
      <circle cx="15" cy="10" r="4.2" fill="#002776" />
    </svg>
  )
}

const FLAGS: Record<Locale, () => React.JSX.Element> = {
  en: UsFlag,
  es: MxFlag,
  pt: BrFlag,
}

export function LocaleFlag({ locale }: { locale: Locale }) {
  const Flag = FLAGS[locale]
  return <Flag />
}
