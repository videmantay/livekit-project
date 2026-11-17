import { useState, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { errorText } from './errors'

/** A two-step button for irreversible actions: the first click asks, the second does it. */
export function ConfirmButton({
  label,
  confirmLabel,
  warning,
  onConfirm,
}: {
  label: string
  confirmLabel: string
  warning: ReactNode
  onConfirm: () => Promise<void>
}) {
  const [asking, setAsking] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()

  if (!asking) {
    return (
      <Button variant="destructive" onClick={() => setAsking(true)}>
        {label}
      </Button>
    )
  }

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-destructive/40 p-3">
      <p className="text-sm">{warning}</p>
      <div className="flex gap-2">
        <Button
          variant="danger"
          disabled={busy}
          onClick={async () => {
            setBusy(true)
            setError(undefined)
            try {
              await onConfirm()
              setAsking(false)
            } catch (e) {
              // Stay open, so it's clear the action didn't happen and can be retried.
              setError(errorText(e))
            } finally {
              setBusy(false)
            }
          }}
        >
          {busy ? 'Working…' : confirmLabel}
        </Button>
        <Button
          variant="outline"
          disabled={busy}
          onClick={() => {
            setAsking(false)
            setError(undefined)
          }}
        >
          Cancel
        </Button>
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}
