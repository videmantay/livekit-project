import { useEffect, useRef, useState, type ClipboardEvent, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ApiError, visitorApi, type Terms } from '@/lib/api'
import { preferredTermsLanguage } from '@/lib/terms-language'
import { LinkedInLink, PageHeader, VisitorPage } from './layout'
import { GENERIC_CODE_ERROR, RATE_LIMIT_ERROR } from './messages'

export function GateScreen({
  initialError,
  linkCode,
  onVerified,
}: {
  initialError?: string
  /** A code from an invite link, checked straight away. Checking it uses no session (I1). */
  linkCode?: string
  onVerified: (code: string, terms: Terms) => void
}) {
  const [code, setCode] = useState('')
  const [error, setError] = useState(initialError)
  const [busy, setBusy] = useState(false)
  // A link is checked before the form shows, so a valid one goes straight to the terms.
  const [checkingLink, setCheckingLink] = useState(Boolean(linkCode && !initialError))
  const inFlight = useRef(false)

  async function verify(candidate: string) {
    if (inFlight.current) return
    inFlight.current = true
    setBusy(true)
    setError(undefined)
    try {
      // The terms start in the browser's language when cloud-run offers it, else English.
      onVerified(candidate, await visitorApi.verifyInvite(candidate, preferredTermsLanguage()))
    } catch (err) {
      // A bad link gets the same message as a bad code, and the paste box as a fallback (U1).
      setError(err instanceof ApiError && err.status === 429 ? RATE_LIMIT_ERROR : GENERIC_CODE_ERROR)
      setCheckingLink(false)
    } finally {
      inFlight.current = false
      setBusy(false)
    }
  }

  useEffect(() => {
    if (linkCode && !initialError) void verify(linkCode)
    // Runs once per link. The inFlight guard covers StrictMode's second run.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [linkCode])

  // Codes are case-sensitive and meant to be pasted, so only surrounding whitespace is removed (ADR-3).
  function onPaste(e: ClipboardEvent<HTMLInputElement>) {
    e.preventDefault()
    setCode(e.clipboardData.getData('text').trim())
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = code.trim()
    if (trimmed) await verify(trimmed)
  }

  if (checkingLink) {
    return (
      <VisitorPage>
        <PageHeader eyebrow="By invitation" title="Talk to Lee's AI avatar">
          <p role="status">Checking your invitation…</p>
        </PageHeader>
      </VisitorPage>
    )
  }

  return (
    <VisitorPage>
      <PageHeader eyebrow="By invitation" title="Talk to Lee's AI avatar">
        <p>Open the link in your invitation, or paste its access code here.</p>
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
