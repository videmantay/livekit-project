import { useEffect, type ReactNode } from 'react'
import { ArrowRight, ArrowUpRight, ChevronDown } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LINKEDIN_URL, YOUTUBE_URL } from '@/lib/config'
import heroImage from '@/assets/lee-hero.webp'
import {
  CERTIFICATIONS,
  CHANNELS,
  EDUCATION,
  EXPERIENCE,
  LANGUAGE_NAMES,
  LOCALE_PATHS,
  LOCALES,
  PROJECTS,
  tr,
  UI,
  type Locale,
  type Project,
} from './content'

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

function ProjectCard({ project, locale }: { project: Project; locale: Locale }) {
  const name = tr(project.name, locale)
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
              {name}
              <ArrowUpRight className="size-4" aria-hidden />
            </a>
          ) : (
            name
          )}
        </CardTitle>
        {project.role && <p className="text-sm text-muted-foreground">{tr(project.role, locale)}</p>}
        {!project.role && project.url && (
          <p className="text-sm text-muted-foreground">{new URL(project.url).hostname}</p>
        )}
      </CardHeader>
      {(project.description || project.tags || project.youtube) && (
        <CardContent className="flex flex-col gap-3">
          {project.description && (
            <p className="text-[15px]/relaxed text-body">{tr(project.description, locale)}</p>
          )}
          {project.youtube && (
            <a
              href={project.youtube}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex w-fit items-center gap-1.5 text-sm underline-offset-4 hover:underline"
            >
              <YouTubeIcon className="size-4" />
              {UI[locale].youtubeChannel}
            </a>
          )}
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

// Brand marks aren't in lucide, so the LinkedIn logo is drawn inline.
function LinkedInIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-5" fill="currentColor" aria-hidden>
      <path d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28ZM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13ZM7.12 20.45H3.56V9h3.56v11.45ZM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0Z" />
    </svg>
  )
}

function YouTubeIcon({ className = 'size-5' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden>
      <path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.6 12 3.6 12 3.6s-7.5 0-9.4.5A3 3 0 0 0 .5 6.2 31.4 31.4 0 0 0 0 12a31.4 31.4 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.5 9.4.5 9.4.5s7.5 0 9.4-.5a3 3 0 0 0 2.1-2.1A31.4 31.4 0 0 0 24 12a31.4 31.4 0 0 0-.5-5.8ZM9.6 15.6V8.4l6.2 3.6-6.2 3.6Z" />
    </svg>
  )
}

function SideBlock({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 border-b border-white/15 pb-6 last:border-0 last:pb-0">
      <h2 className="font-sans text-xs font-semibold tracking-[0.12em] uppercase">{title}</h2>
      {children}
    </div>
  )
}

function SideLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a
      href={href}
      className="inline-flex w-fit items-center gap-1.5 border-b border-hero-foreground pb-0.5 text-xs font-semibold tracking-[0.08em] uppercase hover:text-hero-muted"
    >
      {children}
      <ArrowRight className="size-3.5" aria-hidden />
    </a>
  )
}

// Dark hero modelled on the reference design: heading on the left, Lee's cutout in the
// centre fading into the background, and short blocks down the right.
function Hero({ locale }: { locale: Locale }) {
  const ui = UI[locale]
  return (
    <section className="relative isolate overflow-hidden bg-hero text-hero-foreground">
      <div className="mx-auto grid max-w-6xl gap-12 px-4 pt-12 pb-16 sm:px-6 lg:min-h-[680px] lg:grid-cols-[1fr_15rem] lg:items-center lg:py-20">
        <div className="relative z-10 flex flex-col gap-6 lg:max-w-sm">
          <span className="h-1 w-20 bg-hero-foreground" aria-hidden />
          <h1 className="text-4xl leading-[1.05] font-bold tracking-[-0.02em] sm:text-6xl">
            {ui.heading}
          </h1>
          <p className="text-base/relaxed text-hero-muted">{ui.summary}</p>
          <a
            href="#projects"
            aria-label={ui.jumpToProjects}
            className="mt-2 grid size-16 place-items-center rounded-full bg-hero-accent transition-transform hover:translate-y-0.5 focus-visible:ring-4 focus-visible:ring-hero-accent/40 focus-visible:outline-none"
          >
            <ChevronDown className="size-7" aria-hidden />
          </a>
        </div>

        <img
          src={heroImage}
          alt="Lee"
          width={1200}
          height={1060}
          fetchPriority="high"
          className="pointer-events-none mx-auto w-full max-w-md [mask-image:linear-gradient(to_bottom,black_70%,transparent)] select-none lg:absolute lg:bottom-0 lg:left-[56%] lg:w-[min(46rem,52%)] lg:max-w-none lg:-translate-x-1/2"
        />

        <aside className="relative z-10 flex flex-col gap-6 text-sm/relaxed text-hero-muted">
          <SideBlock title={ui.aboutTitle}>
            <p>{ui.aboutBody}</p>
            <SideLink href="#experience">{ui.aboutLink}</SideLink>
          </SideBlock>
          <SideBlock title={ui.avatarTitle}>
            <p>{ui.avatarBody}</p>
            <SideLink href="/invite">{ui.avatarLink}</SideLink>
          </SideBlock>
          <SideBlock title={ui.followTitle}>
            <div className="flex items-center gap-4">
              <a
                href={LINKEDIN_URL}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="LinkedIn"
                className="w-fit text-hero-foreground hover:text-hero-muted"
              >
                <LinkedInIcon />
              </a>
              {YOUTUBE_URL && (
                <a
                  href={YOUTUBE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="YouTube"
                  className="w-fit text-hero-foreground hover:text-hero-muted"
                >
                  <YouTubeIcon />
                </a>
              )}
            </div>
          </SideBlock>
        </aside>
      </div>
    </section>
  )
}

// Plain links, so each language has its own URL that can be shared.
function LanguageSwitcher({ locale }: { locale: Locale }) {
  return (
    <ul className="flex items-center text-xs font-semibold tracking-[0.08em]" aria-label={UI[locale].languageLabel}>
      {LOCALES.map((l) => (
        <li key={l}>
          <a
            href={LOCALE_PATHS[l]}
            hrefLang={l}
            lang={l}
            title={LANGUAGE_NAMES[l]}
            aria-label={LANGUAGE_NAMES[l]}
            aria-current={l === locale ? 'page' : undefined}
            className="block rounded px-1.5 py-1 text-hero-muted uppercase hover:text-hero-foreground aria-[current=page]:text-hero-foreground aria-[current=page]:underline aria-[current=page]:underline-offset-4"
          >
            {l}
          </a>
        </li>
      ))}
    </ul>
  )
}

export function LandingPage({ locale = 'en' }: { locale?: Locale }) {
  const ui = UI[locale]

  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])

  return (
    <div className="flex min-h-svh flex-col">
      <header className="sticky top-0 z-20 border-b border-white/10 bg-hero/95 text-hero-foreground backdrop-blur">
        <nav className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6" aria-label={ui.nav.label}>
          <a href="/" className="font-heading text-lg font-bold">
            Lee ViDemantay
          </a>
          <div className="flex items-center gap-2 text-sm sm:gap-4">
            <a href="#projects" className="hidden px-2 py-1 hover:underline sm:inline">
              {ui.nav.projects}
            </a>
            <a href="#channels" className="hidden px-2 py-1 hover:underline sm:inline">
              {ui.nav.channels}
            </a>
            <a href="#experience" className="hidden px-2 py-1 hover:underline sm:inline">
              {ui.nav.experience}
            </a>
            <a href="#education" className="hidden px-2 py-1 hover:underline sm:inline">
              {ui.nav.education}
            </a>
            <LanguageSwitcher locale={locale} />
            <Button asChild size="sm" variant="secondary">
              <a href="/invite">
                <span className="sm:hidden">{ui.inviteShort}</span>
                <span className="hidden sm:inline">{ui.invite}</span>
              </a>
            </Button>
          </div>
        </nav>
      </header>

      <Hero locale={locale} />

      <main className="mx-auto flex w-full max-w-4xl flex-col gap-16 px-4 py-12 sm:px-6 sm:py-16">
        <Section id="projects" title={ui.nav.projects}>
          <div className="grid gap-4 md:grid-cols-2">
            {PROJECTS.map((p) => (
              <ProjectCard key={tr(p.name, 'en')} project={p} locale={locale} />
            ))}
          </div>
        </Section>

        <Section id="channels" title={ui.channelsTitle}>
          <ul className="grid gap-4 md:grid-cols-3">
            {CHANNELS.map((c) => (
              <li key={c.url} lang={c.language}>
                <a
                  href={c.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex h-full items-start gap-3 rounded-xl border p-4 transition-colors hover:bg-muted"
                >
                  <YouTubeIcon className="mt-0.5 size-5 shrink-0" />
                  <span className="flex flex-col gap-0.5">
                    <span className="inline-flex items-center gap-1 font-semibold">
                      {c.name}
                      <ArrowUpRight className="size-4" aria-hidden />
                    </span>
                    <span className="text-sm text-muted-foreground" lang={locale}>
                      {ui.inLanguage[c.language]}
                    </span>
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </Section>

        <Section id="experience" title={ui.nav.experience}>
          <ol className="flex flex-col gap-6 border-l pl-5">
            {EXPERIENCE.map((r) => (
              <li key={`${r.org}-${tr(r.title, 'en')}`} className="flex flex-col gap-1">
                <p className="font-semibold">
                  {tr(r.title, locale)}, {r.org}
                </p>
                <p className="text-sm text-muted-foreground">{tr(r.dates, locale)}</p>
                <p className="text-[15px]/relaxed text-body">{tr(r.description, locale)}</p>
              </li>
            ))}
          </ol>
        </Section>

        <Section id="education" title={ui.nav.education}>
          <div className="grid gap-6 md:grid-cols-2">
            <ul className="flex flex-col gap-3">
              {EDUCATION.map((e) => (
                <li key={e.org}>
                  <p className="font-semibold">{tr(e.title, locale)}</p>
                  <p className="text-sm text-muted-foreground">{e.org}</p>
                </li>
              ))}
            </ul>
            <div className="flex flex-col gap-3">
              <h3 className="text-sm tracking-[0.08em] text-faint uppercase">{ui.certifications}</h3>
              <ul className="flex flex-col gap-3">
                {CERTIFICATIONS.map((c) => (
                  <li key={c.org}>
                    <p className="font-semibold">{tr(c.title, locale)}</p>
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
          <div className="flex items-center gap-4">
            <a href={LINKEDIN_URL} target="_blank" rel="noopener noreferrer" className="hover:underline">
              LinkedIn
            </a>
            {YOUTUBE_URL && (
              <a href={YOUTUBE_URL} target="_blank" rel="noopener noreferrer" className="hover:underline">
                YouTube
              </a>
            )}
          </div>
        </div>
      </footer>
    </div>
  )
}
