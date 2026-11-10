import { useRef, useState, type ClipboardEvent, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ApiError, visitorApi, type Terms } from '@/lib/api'
import { LinkedInLink, PageHeader, VisitorPage } from './layout'
import { GENERIC_CODE_ERROR, RATE_LIMIT_ERROR } from './messages'

export function GateScreen({
  initialError,
  onVerified,
}: {
  initialError?: string
  onVerified: (code: string, terms: Terms) => void
}) {
  const [code, setCode] = useState('')
  const [error, setError] = useState(initialError)
  const [busy, setBusy] = useState(false)
  const inFlight = useRef(false)

  // Codes are case-sensitive and meant to be pasted, so only surrounding whitespace is removed (ADR-3).
  function onPaste(e: ClipboardEvent<HTMLInputElement>) {
    e.preventDefault()
    setCode(e.clipboardData.getData('text').trim())
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = code.trim()
    if (!trimmed || inFlight.current) return
    inFlight.current = true
    setBusy(true)
    setError(undefined)
    try {
      onVerified(trimmed, await visitorApi.verifyInvite(trimmed))
    } catch (err) {
      setError(err instanceof ApiError && err.status === 429 ? RATE_LIMIT_ERROR : GENERIC_CODE_ERROR)
    } finally {
      inFlight.current = false
      setBusy(false)
    }
  }

  return (
    <VisitorPage>
      <PageHeader eyebrow="By invitation" title="Talk to Lee's AI avatar">
        <p>Paste the access code from your invitation.</p>
      </PageHeader>

      <form onSubmit={onSubmit} className="flex flex-col gap-3" noValidate>
        <Label htmlFor="code">Access code</Label>
        <div className="flex flex-wrap gap-2.5">
          <Input
            id="code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            onPaste={onPaste}
            autoComplete="off"
            autoCapitalize="off"
            autoCorrect="off"
            spellCheck={false}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? 'code-error' : undefined}
            className="h-12 flex-[1_1_260px] font-mono"
          />
          <Button type="submit" size="lg" className="h-12" disabled={busy || !code.trim()}>
            {busy ? 'Checking…' : 'Continue'}
          </Button>
        </div>
        {error && (
          <p id="code-error" role="alert" className="text-sm text-error">
            {error}
          </p>
        )}
      </form>

      <p className="text-muted-foreground">
        No code? Ask for an invitation through <LinkedInLink />.
      </p>
      <p>
        <a href="/" className="text-sm text-muted-foreground underline underline-offset-4">
          Back to Lee's portfolio
        </a>
      </p>
    </VisitorPage>
  )
}
