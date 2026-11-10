import { useRef, useState, type FormEvent } from 'react'
import { Mic } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { Contact } from '@/lib/api'
import { MAX_SESSION_MINUTES } from '@/lib/config'
import { PageHeader, VisitorPage } from './layout'

export function ContactScreen({
  onBack,
  onStart,
}: {
  onBack: () => void
  /** Resolves with an error message to show, or nothing if the flow moved on. */
  onStart: (contact: Contact | undefined) => Promise<string | undefined>
}) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [company, setCompany] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)
  // A second click would spend a second session (I9), so guard synchronously as well as disabling.
  const inFlight = useRef(false)

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (inFlight.current) return
    if (!e.currentTarget.reportValidity()) return
    inFlight.current = true
    setBusy(true)
    setError(undefined)

    const contact: Contact = {}
    if (name.trim()) contact.name = name.trim()
    if (email.trim()) contact.email = email.trim()
    if (company.trim()) contact.company = company.trim()

    const message = await onStart(Object.keys(contact).length ? contact : undefined)
    if (message) {
      setError(message)
      inFlight.current = false
      setBusy(false)
    }
  }

  return (
    <VisitorPage>
      <PageHeader eyebrow="Step 2 of 2" title="Leave your details (optional)">
        <p>
          If you'd like Lee to get back to you, leave your details here. They go straight to Lee, not to the avatar.
          You can leave them all blank.
        </p>
      </PageHeader>

      <form onSubmit={onSubmit} className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <Label htmlFor="name">Name</Label>
          <Input id="name" value={name} onChange={(e) => setName(e.target.value)} maxLength={120} autoComplete="name" />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            maxLength={254}
            autoComplete="email"
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="company">Company</Label>
          <Input
            id="company"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            maxLength={120}
            autoComplete="organization"
          />
        </div>

        <p className="text-muted-foreground">
          Starting uses one of the sessions on your invite, even if your microphone or connection then fails. The call
          lasts up to {MAX_SESSION_MINUTES} minutes, and your browser will ask for your microphone next.
        </p>

        {error && (
          <p role="alert" className="text-sm text-error">
            {error}
          </p>
        )}

        <div className="flex flex-wrap gap-3">
          <Button type="submit" size="xl" data-icon="inline-start" disabled={busy}>
            <Mic />
            {busy ? 'Starting…' : 'Start the call'}
          </Button>
          <Button type="button" variant="ghost" size="xl" onClick={onBack} disabled={busy}>
            Back to the terms
          </Button>
        </div>
      </form>
    </VisitorPage>
  )
}
