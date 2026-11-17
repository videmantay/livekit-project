import { useEffect, useState, type FormEvent } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  adminApi,
  FACT_SECTIONS,
  type Fact,
  type FactSection,
  type FactsState,
  type Story,
} from '@/lib/admin-api'
import { errorText } from './errors'
import { formatDateTime } from './format'

type Change = 'new' | 'edited' | 'published'

const EMPTY: Fact = { id: '', section: 'experience', topic: '', level: '', verified: '', limits: '', stories: [] }

const EMPTY_STORY: Story = { title: '', situation: '', task: '', action: '', result: '' }

const STORY_PARTS = [
  ['situation', 'Situation', 'Where Lee was and what was going on'],
  ['task', 'Task', 'What Lee had to do'],
  ['action', 'Action', "What Lee did, in Lee's words"],
  ['result', 'Result', 'What changed. Use a real number only if Lee confirmed it'],
] as const

const sameFact = ({ id: _a, ...a }: Fact, { id: _b, ...b }: Fact) => JSON.stringify(a) === JSON.stringify(b)

/** `seed` is a declined question from "Add as fact". Remount with a new key to apply another. */
export function FactsPage({ seed }: { seed?: string }) {
  const [state, setState] = useState<FactsState>()
  const [editing, setEditing] = useState<Fact | undefined>(seed ? { ...EMPTY, topic: seed } : undefined)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()

  useEffect(() => {
    adminApi.getFacts().then(setState, (e) => setError(errorText(e)))
  }, [])

  if (!state) return <p className={error ? 'text-destructive' : 'text-muted-foreground'}>{error ?? 'Loading…'}</p>

  const latest = state.versions.at(-1)
  const published = new Map(latest?.facts.map((f) => [f.id, f]))
  const changeOf = (fact: Fact): Change => {
    const p = published.get(fact.id)
    if (!p) return 'new'
    return sameFact(p, fact) ? 'published' : 'edited'
  }
  const removed = latest?.facts.filter((f) => !state.working.some((w) => w.id === f.id)) ?? []
  const pending = state.working.filter((f) => changeOf(f) !== 'published').length + removed.length

  async function run(action: () => Promise<FactsState>): Promise<boolean> {
    setBusy(true)
    setError(undefined)
    try {
      setState(await action())
      return true
    } catch (e) {
      setError(errorText(e))
      return false
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-medium">
              {latest ? `Version ${latest.number} is live` : 'Nothing published yet'}
              {latest && <span className="font-normal text-muted-foreground"> · {formatDateTime(latest.publishedAt)}</span>}
            </p>
            <p className="text-sm text-muted-foreground">
              Only published facts reach the avatar, from the next call on. Treat everything you publish as public.
            </p>
          </div>
          <Button disabled={busy || pending === 0} onClick={() => run(() => adminApi.publishFacts())}>
            {pending ? `Publish ${pending} ${pending === 1 ? 'change' : 'changes'}` : 'No changes to publish'}
          </Button>
        </CardContent>
      </Card>

      {error && <p className="rounded-lg border border-destructive px-4 py-3 text-sm text-destructive">{error}</p>}

      {editing ? (
        <FactEditor
          key={editing.id || 'new'}
          fact={editing}
          busy={busy}
          onCancel={() => setEditing(undefined)}
          onSave={async (fact) => {
            if (await run(() => adminApi.saveFact(fact))) setEditing(undefined)
          }}
        />
      ) : (
        <div>
          <Button variant="outline" onClick={() => setEditing(EMPTY)}>
            Add a fact
          </Button>
        </div>
      )}

      <section className="flex flex-col gap-3">
        <h2 className="text-xl font-semibold">Facts</h2>
        {state.working.map((fact) => {
          const change = changeOf(fact)
          return (
            <Card key={fact.id} size="sm">
              <CardHeader>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <CardTitle className="text-base">
                    {fact.topic}
                    <span className="font-normal text-muted-foreground"> · {FACT_SECTIONS[fact.section]}</span>
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    {change === 'published' ? (
                      <Badge variant="secondary">Published</Badge>
                    ) : (
                      <Badge variant="outline">{change === 'new' ? 'Draft, new' : 'Draft, edited'}</Badge>
                    )}
                    <Button size="sm" variant="outline" onClick={() => setEditing(fact)} disabled={busy}>
                      Edit
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => run(() => adminApi.deleteFact(fact.id))} disabled={busy}>
                      Remove
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="grid gap-2 text-sm sm:grid-cols-[100px_minmax(0,1fr)]">
                <span className="text-muted-foreground">Level</span>
                <span>{fact.level}</span>
                <span className="text-muted-foreground">Verified</span>
                <span>{fact.verified}</span>
                <span className="text-muted-foreground">Limits</span>
                <span>{fact.limits}</span>
                {fact.stories.map((story, i) => (
                  <div key={i} className="contents">
                    <span className="text-muted-foreground">Story</span>
                    <div className="flex flex-col gap-1">
                      <span className="font-medium">{story.title}</span>
                      {STORY_PARTS.map(([key, label]) => (
                        <span key={key}>
                          <span className="text-muted-foreground">{label}: </span>
                          {story[key]}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )
        })}
        {removed.map((fact) => (
          <p key={fact.id} className="rounded-lg border border-dashed px-4 py-3 text-sm text-muted-foreground">
            <span className="line-through">{fact.topic}</span> will be removed when you publish.
          </p>
        ))}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-xl font-semibold">Versions</h2>
        {[...state.versions].reverse().map((v) => (
          <div key={v.number} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3">
            <p className="text-sm">
              <span className="font-medium">Version {v.number}</span>
              <span className="text-muted-foreground">
                {' '}
                · {formatDateTime(v.publishedAt)} · {v.facts.length} {v.facts.length === 1 ? 'fact' : 'facts'}
              </span>
            </p>
            {v.number === latest?.number ? (
              <Badge variant="secondary">Live</Badge>
            ) : (
              <Button size="sm" variant="outline" disabled={busy} onClick={() => run(() => adminApi.rollbackFacts(v.number))}>
                Roll back to this
              </Button>
            )}
          </div>
        ))}
        <p className="text-sm text-muted-foreground">
          Rolling back publishes that version's facts as a new version and discards unpublished drafts.
        </p>
      </section>
    </div>
  )
}

function FactEditor({
  fact,
  busy,
  onSave,
  onCancel,
}: {
  fact: Fact
  busy: boolean
  onSave: (fact: Fact) => Promise<void>
  onCancel: () => void
}) {
  const [draft, setDraft] = useState(fact)
  const set = (key: 'topic' | 'level' | 'verified' | 'limits') => (e: { target: { value: string } }) =>
    setDraft({ ...draft, [key]: e.target.value })
  const setStory = (index: number, key: keyof Story, value: string) =>
    setDraft({ ...draft, stories: draft.stories.map((s, i) => (i === index ? { ...s, [key]: value } : s)) })

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    await onSave(draft)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{fact.id ? 'Edit fact' : 'New fact'}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="fact-section">Section</Label>
            <Select value={draft.section} onValueChange={(v) => setDraft({ ...draft, section: v as FactSection })}>
              <SelectTrigger id="fact-section" className="w-full sm:w-64">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(FACT_SECTIONS).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="fact-topic">Topic</Label>
            <Input id="fact-topic" value={draft.topic} onChange={set('topic')} required />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="fact-level">Level</Label>
            <Input id="fact-level" value={draft.level} onChange={set('level')} placeholder='For example "Senior", or "None"' required />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="fact-verified">What's verified</Label>
            <Textarea id="fact-verified" value={draft.verified} onChange={set('verified')} required />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="fact-limits">Limits</Label>
            <Textarea
              id="fact-limits"
              value={draft.limits}
              onChange={set('limits')}
              placeholder="What Lee hasn't done, and what the avatar must not claim"
            />
          </div>
          <fieldset className="flex flex-col gap-4">
            <legend className="font-medium">STAR stories</legend>
            <p className="text-sm text-muted-foreground">
              When a visitor asks for an example, the avatar tells a story in this order, using only what you write here.
              A fact with no story gets its verified facts and a pointer to you.
            </p>
            {draft.stories.map((story, i) => (
              <div key={i} className="flex flex-col gap-3 rounded-lg border p-4">
                <div className="flex flex-col gap-2">
                  <Label htmlFor={`story-${i}-title`}>Story title</Label>
                  <Input
                    id={`story-${i}-title`}
                    value={story.title}
                    onChange={(e) => setStory(i, 'title', e.target.value)}
                    placeholder='For example "Replacing the manual 3D request workflow"'
                    required
                  />
                </div>
                {STORY_PARTS.map(([key, label, hint]) => (
                  <div key={key} className="flex flex-col gap-2">
                    <Label htmlFor={`story-${i}-${key}`}>{label}</Label>
                    <Textarea
                      id={`story-${i}-${key}`}
                      value={story[key]}
                      onChange={(e) => setStory(i, key, e.target.value)}
                      placeholder={hint}
                      required
                    />
                  </div>
                ))}
                <div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setDraft({ ...draft, stories: draft.stories.filter((_, j) => j !== i) })}
                  >
                    Remove story
                  </Button>
                </div>
              </div>
            ))}
            <div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={draft.stories.length >= 10}
                onClick={() => setDraft({ ...draft, stories: [...draft.stories, { ...EMPTY_STORY }] })}
              >
                Add a story
              </Button>
            </div>
          </fieldset>
          <p className="text-sm text-muted-foreground">Saving keeps this as a draft. It reaches the avatar only when you publish.</p>
          <div className="flex gap-2">
            <Button type="submit" disabled={busy}>
              Save draft
            </Button>
            <Button type="button" variant="outline" onClick={onCancel} disabled={busy}>
              Cancel
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
