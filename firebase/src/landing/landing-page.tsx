import type { ReactNode } from 'react'
import { ArrowUpRight, Mic } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LINKEDIN_URL } from '@/lib/config'
import { CERTIFICATIONS, EDUCATION, EXPERIENCE, INTRO, PROJECTS, type Project } from './content'

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="flex scroll-mt-20 flex-col gap-5">
      <h2 id={`${id}-title`} className="text-2xl font-bold">
        {title}
      </h2>
      {children}
    </section>
  )
}

function ProjectCard({ project }: { project: Project }) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-lg">
          {project.url ? (
            <a
              href={project.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 underline-offset-4 hover:underline"
            >
              {project.name}
              <ArrowUpRight className="size-4" aria-hidden />
            </a>
          ) : (
            project.name
          )}
        </CardTitle>
        {project.role && <p className="text-sm text-muted-foreground">{project.role}</p>}
        {!project.role && project.url && (
          <p className="text-sm text-muted-foreground">{new URL(project.url).hostname}</p>
        )}
      </CardHeader>
      {(project.description || project.tags) && (
        <CardContent className="flex flex-col gap-3">
          {project.description && <p className="text-[15px]/relaxed text-body">{project.description}</p>}
          {project.tags && (
            <div className="flex flex-wrap gap-1.5">
              {project.tags.map((t) => (
                <Badge key={t} variant="secondary">
                  {t}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}

export function LandingPage() {
  return (
    <div className="flex min-h-svh flex-col">
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
        <nav className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-4 py-3 sm:px-6" aria-label="Main">
          <a href="/" className="font-heading text-lg font-bold">
            Lee
          </a>
          <div className="flex items-center gap-1 text-sm sm:gap-4">
            <a href="#projects" className="hidden px-2 py-1 hover:underline sm:inline">
              Projects
            </a>
            <a href="#experience" className="hidden px-2 py-1 hover:underline sm:inline">
              Experience
            </a>
            <a href="#education" className="hidden px-2 py-1 hover:underline sm:inline">
              Education
            </a>
            <Button asChild size="sm">
              <a href="/invite">I have an invite</a>
            </Button>
          </div>
        </nav>
      </header>

      <main className="mx-auto flex w-full max-w-4xl flex-col gap-16 px-4 py-12 sm:px-6 sm:py-16">
        <section className="flex flex-col gap-5">
          <p className="text-sm tracking-[0.12em] text-muted-foreground uppercase">{INTRO.role}</p>
          <h1 className="text-4xl leading-tight font-bold tracking-[-0.02em] sm:text-6xl">Hi, I'm Lee.</h1>
          <p className="max-w-2xl text-lg/relaxed text-muted-foreground">{INTRO.summary}</p>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg" variant="outline">
              <a href={LINKEDIN_URL} target="_blank" rel="noopener noreferrer">
                LinkedIn
              </a>
            </Button>
            <Button asChild size="lg" variant="ghost">
              <a href="#projects">See my projects</a>
            </Button>
          </div>
        </section>

        <Card className="border-foreground/20">
          <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-col gap-1">
              <p className="text-lg font-semibold">Talk to my AI avatar</p>
              <p className="text-muted-foreground">
                Have an invite code? Ask my AI avatar about my work, by voice. No code? Ask me on{' '}
                <a href={LINKEDIN_URL} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4">
                  LinkedIn
                </a>
                .
              </p>
            </div>
            <Button asChild size="lg" data-icon="inline-start" className="shrink-0">
              <a href="/invite">
                <Mic />
                Enter invite code
              </a>
            </Button>
          </CardContent>
        </Card>

        <Section id="projects" title="Projects">
          <div className="grid gap-4 md:grid-cols-2">
            {PROJECTS.map((p) => (
              <ProjectCard key={p.name} project={p} />
            ))}
          </div>
        </Section>

        <Section id="experience" title="Experience">
          <ol className="flex flex-col gap-6 border-l pl-5">
            {EXPERIENCE.map((r) => (
              <li key={`${r.org}-${r.title}`} className="flex flex-col gap-1">
                <p className="font-semibold">
                  {r.title}, {r.org}
                </p>
                <p className="text-sm text-muted-foreground">{r.dates}</p>
                <p className="text-[15px]/relaxed text-body">{r.description}</p>
              </li>
            ))}
          </ol>
        </Section>

        <Section id="education" title="Education">
          <div className="grid gap-6 md:grid-cols-2">
            <ul className="flex flex-col gap-3">
              {EDUCATION.map((e) => (
                <li key={e.title}>
                  <p className="font-semibold">{e.title}</p>
                  <p className="text-sm text-muted-foreground">{e.org}</p>
                </li>
              ))}
            </ul>
            <div className="flex flex-col gap-3">
              <h3 className="text-sm tracking-[0.08em] text-faint uppercase">Certifications</h3>
              <ul className="flex flex-col gap-3">
                {CERTIFICATIONS.map((c) => (
                  <li key={c.title}>
                    <p className="font-semibold">{c.title}</p>
                    <p className="text-sm text-muted-foreground">
                      {c.org}
                      {c.detail && ` · ${c.detail}`}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Section>
      </main>

      <footer className="mt-auto border-t">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-3 px-4 py-6 text-sm text-muted-foreground sm:px-6">
          <span>Lee</span>
          <a href={LINKEDIN_URL} target="_blank" rel="noopener noreferrer" className="hover:underline">
            LinkedIn
          </a>
        </div>
      </footer>
    </div>
  )
}
