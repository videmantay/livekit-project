import { useState } from 'react'
import { TermsText } from '@/components/terms-text'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import type { Terms } from '@/lib/api'
import { MAX_SESSION_MINUTES } from '@/lib/config'
import { PageHeader, VisitorPage } from './layout'

export function TermsScreen({
  terms,
  notice,
  onAccept,
}: {
  terms: Terms
  notice?: string
  onAccept: () => void
}) {
  // Always starts unticked, including after a 409 reload (I2, I3).
  const [agreed, setAgreed] = useState(false)

  return (
    <VisitorPage>
      <PageHeader eyebrow="Step 1 of 2" title="Before you start">
        <p>Please read how the conversation works and what is kept.</p>
      </PageHeader>

      {notice && (
        <p role="alert" className="rounded-lg border border-foreground/20 bg-muted px-4 py-3">
          {notice}
        </p>
      )}

      <Card>
        <CardContent className="max-h-[50vh] overflow-y-auto">
          <TermsText text={terms.text} />
        </CardContent>
      </Card>

      <p className="text-muted-foreground">
        Calls last up to {MAX_SESSION_MINUTES} minutes. Your microphone is only requested after you agree and start
        the call.
      </p>

      <div className="flex items-start gap-3">
        <Checkbox id="agree" checked={agreed} onCheckedChange={(v) => setAgreed(v === true)} className="mt-1" />
        <Label htmlFor="agree" className="text-base/snug font-normal">
          I have read this and agree to my conversation being transcribed, stored and reviewed as described.
        </Label>
      </div>

      <div>
        <Button size="lg" disabled={!agreed} onClick={onAccept}>
          Continue
        </Button>
      </div>
    </VisitorPage>
  )
}
