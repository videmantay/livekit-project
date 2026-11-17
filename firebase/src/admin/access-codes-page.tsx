import { useEffect, useState, type FormEvent } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { adminApi, type Invite } from '@/lib/admin-api'
import { inviteLink, inviteMessage } from '@/lib/invite-link'
import { ConfirmButton } from './confirm-button'
import { errorText } from './errors'
import { formatDate } from './format'

function status(invite: Invite): { text: string; variant: 'secondary' | 'outline' | 'destructive' } {
  if (invite.revoked) return { text: 'Revoked', variant: 'destructive' }
  if (new Date(invite.expiresAt) < new Date()) return { text: 'Expired', variant: 'outline' }
  if (invite.sessionsUsed >= invite.sessionLimit) return { text: 'Used up', variant: 'outline' }
  return { text: 'Active', variant: 'secondary' }
}

export function AccessCodesPage() {
  const [invites, setInvites] = useState<Invite[]>()
  const [newCode, setNewCode] = useState<{ invite: Invite; code: string }>()
  const [loadError, setLoadError] = useState<string>()

  useEffect(() => {
    adminApi.listInvites().then(setInvites, (e) => setLoadError(errorText(e)))
  }, [])

  return (
    <div className="flex flex-col gap-6">
      <CreateInviteForm
        onCreated={(invite, code) => {
          setInvites((prev) => [invite, ...(prev ?? [])])
          setNewCode({ invite, code })
        }}
      />

      {newCode && <NewCodePanel {...newCode} onDone={() => setNewCode(undefined)} />}

      <section className="flex flex-col gap-3">
        <h2 className="text-xl font-semibold">Invites</h2>
        {!invites ? (
          <p className={loadError ? 'text-destructive' : 'text-muted-foreground'}>{loadError ?? 'Loading…'}</p>
        ) : !invites.length ? (
          <p className="text-muted-foreground">No invites yet.</p>
        ) : (
          // Labels only. Codes are stored as hashes and can never be shown again (A1, ADR-10).
          invites.map((invite) => {
            const s = status(invite)
            return (
              <Card key={invite.id} size="sm">
                <CardContent className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{invite.label}</span>
                      <Badge variant={s.variant}>{s.text}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {invite.sessionsUsed} of {invite.sessionLimit} sessions used · expires {formatDate(invite.expiresAt)}
                    </p>
                  </div>
                  {!invite.revoked && (
                    <ConfirmButton
                      label="Revoke"
                      confirmLabel="Revoke now"
                      warning="The code stops working immediately. This can't be undone."
                      onConfirm={async () => {
                        const updated = await adminApi.revokeInvite(invite.id)
                        setInvites((prev) => prev?.map((i) => (i.id === updated.id ? updated : i)))
                      }}
                    />
                  )}
                </CardContent>
              </Card>
            )
          })
        )}
      </section>
    </div>
  )
}

function CreateInviteForm({ onCreated }: { onCreated: (invite: Invite, code: string) => void }) {
  const [label, setLabel] = useState('')
  const [sessionLimit, setSessionLimit] = useState(2)
  const [expiresInDays, setExpiresInDays] = useState(14)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (busy || !label.trim()) return
    setBusy(true)
    setError(undefined)
    try {
      const { invite, code } = await adminApi.createInvite({ label: label.trim(), sessionLimit, expiresInDays })
      onCreated(invite, code)
      setLabel('')
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Create an invite</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_120px_120px_auto] sm:items-end">
          <div className="flex flex-col gap-2">
            <Label htmlFor="invite-label">Label</Label>
            <Input
              id="invite-label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Who it's for, e.g. Acme recruiter"
              maxLength={120}
              required
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="invite-limit">Sessions</Label>
            <Input
              id="invite-limit"
              type="number"
              min={1}
              max={10}
              value={sessionLimit}
              onChange={(e) => setSessionLimit(Number(e.target.value))}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="invite-days">Expires in days</Label>
            <Input
              id="invite-days"
              type="number"
              min={1}
              max={90}
              value={expiresInDays}
              onChange={(e) => setExpiresInDays(Number(e.target.value))}
            />
          </div>
          <Button type="submit" size="lg" disabled={busy || !label.trim()}>
            {busy ? 'Creating…' : 'Create'}
          </Button>
        </form>
        {error && (
          <p role="alert" className="mt-3 text-sm text-destructive">
            {error}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

type Copied = 'message' | 'link' | 'code'

// Shown once, straight after creating an invite. The code can't be shown again (A1).
function NewCodePanel({ invite, code, onDone }: { invite: Invite; code: string; onDone: () => void }) {
  const [copied, setCopied] = useState<Copied>()
  const link = inviteLink(code)
  const message = inviteMessage({
    link,
    code,
    sessionLimit: invite.sessionLimit,
    expiresOn: formatDate(invite.expiresAt),
  })

  async function copy(what: Copied, text: string) {
    await navigator.clipboard.writeText(text)
    setCopied(what)
  }

  return (
    <Card className="border-foreground/30">
      <CardHeader>
        <CardTitle className="text-lg">Invite for “{invite.label}”</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm">
          Copy it now. It's shown only once and can't be recovered. Send the link; the code is the
          fallback if an email client breaks the link.
        </p>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="invite-message">Email message</Label>
          <textarea
            id="invite-message"
            readOnly
            value={message}
            rows={14}
            onFocus={(e) => e.currentTarget.select()}
            className="w-full resize-y rounded-lg border bg-muted px-3 py-2 text-sm leading-relaxed"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Link</span>
          <code className="rounded-lg bg-muted px-3 py-2 font-mono text-sm break-all select-all">{link}</code>
        </div>

        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Code</span>
          <code className="rounded-lg bg-muted px-3 py-2 font-mono text-sm break-all select-all">{code}</code>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button onClick={() => copy('message', message)}>
            {copied === 'message' ? 'Copied' : 'Copy message'}
          </Button>
          <Button variant="outline" onClick={() => copy('link', link)}>
            {copied === 'link' ? 'Copied' : 'Copy link'}
          </Button>
          <Button variant="outline" onClick={() => copy('code', code)}>
            {copied === 'code' ? 'Copied' : 'Copy code'}
          </Button>
          <Button variant="secondary" onClick={onDone}>
            Done, hide it
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
