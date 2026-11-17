import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { adminApi, type Conversation } from '@/lib/admin-api'
import { ConfirmButton } from './confirm-button'
import { errorText } from './errors'
import { formatDateTime, formatDuration } from './format'

export function ConversationsPage({ onAddAsFact }: { onAddAsFact: (question: string) => void }) {
  const [items, setItems] = useState<Conversation[]>()
  const [openId, setOpenId] = useState<string>()
  const [error, setError] = useState<string>()

  useEffect(() => {
    adminApi.listConversations().then(setItems, (e) => setError(errorText(e)))
  }, [])

  if (!items) return <p className={error ? 'text-destructive' : 'text-muted-foreground'}>{error ?? 'Loading…'}</p>
  if (!items.length) return <p className="text-muted-foreground">No conversations yet.</p>

  return (
    <div className="flex flex-col gap-4">
      {items.map((c) => (
        <Card key={c.id}>
          <CardHeader>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <CardTitle className="text-lg">{c.inviteLabel}</CardTitle>
              <p className="text-sm text-muted-foreground">
                {formatDateTime(c.startedAt)} ·{' '}
                {c.status === 'ended' ? formatDuration(c.durationSeconds) : STATUS_TEXT[c.status]}
              </p>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <Summary conversation={c} />

            {c.declinedQuestions.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="text-xs tracking-[0.08em] text-faint uppercase">Declined questions</p>
                {c.declinedQuestions.map((q) => (
                  <div key={q} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-muted px-3 py-2">
                    <span>{q}</span>
                    <Button size="sm" variant="outline" onClick={() => onAddAsFact(q)}>
                      Add as fact
                    </Button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => setOpenId(openId === c.id ? undefined : c.id)}>
                {openId === c.id ? 'Hide transcript' : 'Show transcript'}
              </Button>
              {c.contact ? <Badge variant="secondary">Left contact details</Badge> : null}
              {c.factsVersion !== null && <Badge variant="outline">Facts v{c.factsVersion}</Badge>}
              {c.transcript.some((t) => t.violation) && <Badge variant="destructive">Flagged turns</Badge>}
            </div>

            {openId === c.id && <ConversationDetail conversation={c} />}

            <div>
              <ConfirmButton
                label="Delete this person's data"
                confirmLabel="Delete permanently"
                warning="This deletes the session, transcript, summary and contact details. It can't be undone."
                onConfirm={async () => {
                  await adminApi.deleteConversation(c.id)
                  setItems((prev) => prev?.filter((x) => x.id !== c.id))
                }}
              />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

const STATUS_TEXT = { created: 'Not started', active: 'In progress' } as const

function Summary({ conversation: c }: { conversation: Conversation }) {
  const note =
    c.status !== 'ended'
      ? 'The summary is written when the call ends.'
      : c.summaryStatus === 'empty'
        ? 'Nothing was said, so there is no summary.'
        : c.summaryStatus === 'failed'
          ? "The summary couldn't be written. The transcript is saved."
          : !c.summaryStatus
            ? 'The call ended. The summary is being written.'
            : undefined
  return (
    <div>
      <p className="text-xs tracking-[0.08em] text-faint uppercase">tl;dr</p>
      {note ? (
        <p className="text-muted-foreground">{note}</p>
      ) : (
        <>
          <p>{c.summary}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Written by AI from the transcript. Check it against the transcript before relying on it.
          </p>
        </>
      )}
    </div>
  )
}

function ConversationDetail({ conversation: c }: { conversation: Conversation }) {
  return (
    <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_240px]">
      <div className="flex flex-col gap-2 rounded-lg border p-4 text-sm">
        {c.transcript.length === 0 && <p className="text-muted-foreground">No transcript.</p>}
        {c.transcript.map((turn, i) => (
          <p key={i} className={turn.violation ? 'rounded bg-destructive/10 px-2 py-1' : undefined}>
            <span className="font-semibold">{turn.speaker === 'agent' ? 'Lee (AI)' : 'Visitor'}: </span>
            {turn.text}
            {turn.violation && <span className="ml-2 text-xs text-destructive">Counted as inappropriate</span>}
          </p>
        ))}
      </div>
      <div className="flex flex-col gap-1 rounded-lg border p-4 text-sm">
        <p className="text-xs tracking-[0.08em] text-faint uppercase">Contact details</p>
        {c.contact ? (
          <>
            {c.contact.name && <p>{c.contact.name}</p>}
            {c.contact.email && <p>{c.contact.email}</p>}
            {c.contact.company && <p>{c.contact.company}</p>}
          </>
        ) : (
          <p className="text-muted-foreground">None given</p>
        )}
      </div>
    </div>
  )
}
