import { useEffect, useRef, useState } from 'react'
import { Mic, MicOff, PhoneOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { END_WARNING_MINUTES, MAX_SESSION_MINUTES, PORTUGUESE_CLIP_URL } from '@/lib/config'
import { VisitorPage } from './layout'

export type CallEnd = 'user' | 'time-limit' | 'connection-lost'

const LIMIT_SECONDS = MAX_SESSION_MINUTES * 60

function formatClock(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

// Placeholder transcript until LiveKit's transcription is wired in. Speakers read "Lee (AI)" (ADR-11).
const SAMPLE_TRANSCRIPT = [
  { speaker: 'Lee (AI)', text: "Hi, I'm an AI avatar of Lee, not the real person. What would you like to know?" },
]

export function CallScreen({
  stream,
  failConnection,
  onEnd,
}: {
  stream: MediaStream
  /** Mock only: acts out a dropped connection a few seconds in. */
  failConnection: boolean
  onEnd: (end: CallEnd) => void
}) {
  const [muted, setMuted] = useState(false)
  const [secondsLeft, setSecondsLeft] = useState(LIMIT_SECONDS)
  const onEndRef = useRef(onEnd)
  useEffect(() => {
    onEndRef.current = onEnd
  })

  // Display only: the agent ends the call at the limit, and the browser can't extend it (ADR-5).
  useEffect(() => {
    const startedAt = Date.now()
    const id = setInterval(() => {
      const left = Math.max(0, LIMIT_SECONDS - Math.floor((Date.now() - startedAt) / 1000))
      setSecondsLeft(left)
      if (left === 0) onEndRef.current('time-limit')
    }, 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (!failConnection) return
    const id = setTimeout(() => onEndRef.current('connection-lost'), 5000)
    return () => clearTimeout(id)
  }, [failConnection])

  function toggleMute() {
    const next = !muted
    stream.getAudioTracks().forEach((t) => (t.enabled = !next))
    setMuted(next)
  }

  const warning = secondsLeft <= END_WARNING_MINUTES * 60

  return (
    <VisitorPage wide>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <section className="flex flex-col gap-4" aria-label="Call">
          <div className="relative aspect-video overflow-hidden rounded-2xl border bg-muted">
            {/* The AI label is permanent and can't be dismissed (ADR-11, I6). */}
            <p className="absolute top-3 left-3 rounded-md bg-foreground px-2.5 py-1 text-sm font-semibold text-background">
              AI avatar of Lee, not the real person
            </p>
            <div className="flex h-full items-center justify-center text-muted-foreground">Avatar video</div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="flex items-center gap-2 text-sm" role="status">
              <span className="size-2.5 rounded-full bg-destructive" aria-hidden />
              Transcript being saved
            </p>
            <p className="text-sm text-muted-foreground tabular-nums" aria-live="off">
              {formatClock(secondsLeft)} left
            </p>
          </div>

          {warning && (
            <p role="alert" className="rounded-lg border border-foreground/20 bg-muted px-4 py-3">
              Less than {END_WARNING_MINUTES} minutes left. The call ends automatically at {MAX_SESSION_MINUTES}{' '}
              minutes.
            </p>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="outline"
              size="icon-xl"
              onClick={toggleMute}
              aria-pressed={muted}
              aria-label={muted ? 'Unmute microphone' : 'Mute microphone'}
            >
              {muted ? <MicOff /> : <Mic />}
            </Button>
            <Button variant="danger" size="xl" className="rounded-full" data-icon="inline-start" onClick={() => onEnd('user')}>
              <PhoneOff />
              End session
            </Button>
            {muted && <span className="text-sm text-muted-foreground">You're muted</span>}
          </div>
        </section>

        <aside className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Transcript</CardTitle>
            </CardHeader>
            <CardContent className="flex max-h-80 flex-col gap-3 overflow-y-auto text-sm">
              {SAMPLE_TRANSCRIPT.map((turn, i) => (
                <p key={i}>
                  <span className="font-semibold">{turn.speaker}: </span>
                  {turn.text}
                </p>
              ))}
            </CardContent>
          </Card>
          <PortugueseClip />
        </aside>
      </div>
    </VisitorPage>
  )
}

function PortugueseClip() {
  const [missing, setMissing] = useState(false)
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Lee's real voice, unedited</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 text-sm text-muted-foreground">
        <p>
          The avatar speaks English only. Lee's Spanish is fluent and Lee's Portuguese is about B2. Here is an
          unscripted clip of Lee speaking Portuguese.
        </p>
        {missing ? (
          <p className="italic">The clip isn't available yet.</p>
        ) : (
          <audio controls preload="metadata" src={PORTUGUESE_CLIP_URL} onError={() => setMissing(true)} className="w-full">
            Your browser can't play this clip.
          </audio>
        )}
      </CardContent>
    </Card>
  )
}
