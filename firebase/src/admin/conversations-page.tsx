import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { adminApi, type Conversation } from '@/lib/admin-api'
import { ConfirmButton } from './confirm-button'
import { formatDateTime, formatDuration } from './format'

export function ConversationsPage({ onAddAsFact }: { onAddAsFact: (question: string) => void }) {
  const [items, setItems] = useState<Conversation[]>()
  const [openId, setOpenId] = useState<string>()

  useEffect(() => {
    adminApi.listConversations().then(setItems)
  }, [])

  if (!items) return <p className="text-muted-foreground">Loading…</p>
  if (!items.length) return <p className="text-muted-foreground">No conversations yet.</p>

  return (
    <div className="flex flex-col gap-4">
      {items.map((c) => (
        <Card key={c.id}>
          <CardHeader>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <CardTitle className="text-lg">{c.inviteLabel}</CardTitle>
              <p className="text-sm text-muted-foreground">
                {formatDateTime(c.startedAt)} · {formatDuration(c.durationSeconds)}
              </p>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div>
              <p className="text-xs tracking-[0.08em] text-faint uppercase">tl;dr</p>
              <p>{c.summary}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Written by AI from the transcript. Check it against the transcript before relying on it.
              </p>
            </div>

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
              <Badge variant="outline">Facts v{c.factsVersion}</Badge>
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

function ConversationDetail({ conversation: c }: { conversation: Conversation }) {
  return (
    <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_240px]">
      <div className="flex flex-col gap-2 rounded-lg border p-4 text-sm">
        {c.transcript.map((turn, i) => (
          <p key={i}>
            <span className="font-semibold">{turn.speaker === 'agent' ? 'Lee (AI)' : 'Visitor'}: </span>
            {turn.text}
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
