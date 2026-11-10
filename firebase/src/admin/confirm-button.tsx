import { useState, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'

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
            try {
              await onConfirm()
            } finally {
              setBusy(false)
              setAsking(false)
            }
          }}
        >
          {busy ? 'Working…' : confirmLabel}
        </Button>
        <Button variant="outline" disabled={busy} onClick={() => setAsking(false)}>
          Cancel
        </Button>
      </div>
    </div>
  )
}
