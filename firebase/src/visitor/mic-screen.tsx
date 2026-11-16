import { useRef, useState } from 'react'
import { Mic } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MIC_PROBLEM_TEXT, requestMic, type MicProblem } from '@/lib/mic'
import { PageHeader, VisitorPage } from './layout'

/** The session is already spent (ADR-4), so retrying here costs nothing. */
export function MicScreen({
  problem: initialProblem,
  onGranted,
  onGiveUp,
}: {
  problem: MicProblem
  onGranted: (stream: MediaStream) => void
  onGiveUp: () => void
}) {
  const [problem, setProblem] = useState(initialProblem)
  const [busy, setBusy] = useState(false)
  const inFlight = useRef(false)

  async function retry() {
    if (inFlight.current) return
    inFlight.current = true
    setBusy(true)
    const result = await requestMic()
    inFlight.current = false
    setBusy(false)
    if (result instanceof MediaStream) onGranted(result)
    else setProblem(result)
  }

  return (
    <VisitorPage>
      <PageHeader title="Allow your microphone">
        <p>The avatar needs your microphone to hear you.</p>
      </PageHeader>
      <p role="alert" className="rounded-lg border border-foreground/20 bg-muted px-4 py-3">
        {MIC_PROBLEM_TEXT[problem]}
      </p>
      <div className="flex flex-wrap gap-3">
        <Button size="xl" data-icon="inline-start" onClick={retry} disabled={busy}>
          <Mic />
          {busy ? 'Asking…' : 'Try again'}
        </Button>
        <Button variant="ghost" size="xl" onClick={onGiveUp} disabled={busy}>
          End without calling
        </Button>
      </div>
    </VisitorPage>
  )
}
