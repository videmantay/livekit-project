import type { ReactNode } from 'react'
import { LINKEDIN_URL } from '@/lib/config'

export function VisitorPage({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return (
    <main className={`mx-auto flex w-full flex-col gap-8 px-4 py-10 sm:px-6 sm:py-14 ${wide ? 'max-w-5xl' : 'max-w-2xl'}`}>
      {children}
    </main>
  )
}

export function PageHeader({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: ReactNode }) {
  return (
    <header className="flex flex-col gap-3">
      {eyebrow && <p className="text-sm tracking-[0.12em] text-muted-foreground uppercase">{eyebrow}</p>}
      <h1 className="text-4xl leading-tight font-bold tracking-[-0.02em] sm:text-5xl">{title}</h1>
      {children && <div className="text-lg/relaxed text-muted-foreground">{children}</div>}
    </header>
  )
}

export function LinkedInLink({ children = 'Lee on LinkedIn' }: { children?: ReactNode }) {
  return (
    <a href={LINKEDIN_URL} target="_blank" rel="noopener noreferrer" className="font-medium text-foreground underline underline-offset-4">
      {children}
    </a>
  )
}
