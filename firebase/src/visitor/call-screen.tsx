import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import {
  LiveKitRoom,
  RoomAudioRenderer,
  StartAudio,
  useConnectionState,
  useLocalParticipant,
  useRoomContext,
  useTranscriptions,
  useVoiceAssistant,
  VideoTrack,
} from '@livekit/components-react'
import {
  ConnectionState,
  DisconnectReason,
  ParticipantKind,
  RoomEvent,
  Track,
  type LocalTrackPublication,
  type RemoteParticipant,
} from 'livekit-client'
import { Mic, MicOff, PhoneOff } from 'lucide-react'
import { AgentAudioVisualizerAura } from '@/components/agent-audio-visualizer-aura'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { SessionGrant } from '@/lib/api'
import { END_WARNING_MINUTES, MAX_SESSION_MINUTES } from '@/lib/config'
import { VisitorPage } from './layout'
import { SERVICE_NOTICES } from './messages'

export type CallEnd = 'user' | 'time-limit' | 'connection-lost'

type Turn = { id: string; speaker: string; text: string }

// The agent is always labelled as an AI, never as plain "Lee" (ADR-11, I6).
const AGENT_LABEL = 'Lee (AI)'

const LIMIT_SECONDS = MAX_SESSION_MINUTES * 60

// Set by the agent on its own participant when a provider fails partway (I7). The keys and
// values must match livekit/service_notices.py. Only fixed values arrive, never error text.
const VIDEO_NOTICE = 'notice.video'
const VOICE_NOTICE = 'notice.voice'

function serviceNotices(attributes: Record<string, string> | undefined): string[] {
  const notices: string[] = []
  if (attributes?.[VIDEO_NOTICE] === 'unavailable') notices.push(SERVICE_NOTICES.videoUnavailable)
  if (attributes?.[VOICE_NOTICE] === 'backup') notices.push(SERVICE_NOTICES.backupVoice)
  return notices
}

function formatClock(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export function CallScreen({
  grant,
  stream,
  preview,
  failConnection,
  onEnd,
}: {
  grant: SessionGrant
  /** The visitor's mic, already granted. Live calls publish it; ending the call stops it. */
  stream: MediaStream
  /** No cloud-run, so there is no real room: act the call out locally. */
  preview: boolean
  /** Preview only: acts out a dropped connection a few seconds in. */
  failConnection: boolean
  onEnd: (end: CallEnd) => void
}) {
  // Reports one ending only, whichever comes first: the button, the clock or the network.
  const ended = useRef(false)
  const onEndRef = useRef(onEnd)
  useEffect(() => {
    onEndRef.current = onEnd
  })
  const end = useCallback((reason: CallEnd) => {
    if (ended.current) return
    ended.current = true
    onEndRef.current(reason)
  }, [])

  if (preview) return <PreviewCall stream={stream} failConnection={failConnection} onEnd={end} />
  return (
    <LiveKitRoom
      serverUrl={grant.url}
      token={grant.token}
      connect
      // The mic is published by hand from the stream the visitor already allowed, so there is
      // one permission prompt, asked only after consent (ADR-4). The token allows nothing else.
      audio={false}
      video={false}
      onDisconnected={(reason) => {
        // Our own disconnect, from the button or the clock, already reported its reason.
        if (reason !== DisconnectReason.CLIENT_INITIATED) end('connection-lost')
      }}
      onError={() => end('connection-lost')}
      className="contents"
    >
      <LiveCall stream={stream} onEnd={end} />
    </LiveKitRoom>
  )
}

function LiveCall({ stream, onEnd }: { stream: MediaStream; onEnd: (end: CallEnd) => void }) {
  const room = useRoomContext()
  const connection = useConnectionState()
  const { localParticipant } = useLocalParticipant()
  const { videoTrack, audioTrack, state: agentState, agentAttributes } = useVoiceAssistant()
  const notices = serviceNotices(agentAttributes)
  const voiceOnly = agentAttributes?.[VIDEO_NOTICE] === 'unavailable'
  const transcriptions = useTranscriptions()
  const [muted, setMuted] = useState(false)
  const mutedRef = useRef(false)
  const publication = useRef<LocalTrackPublication | undefined>(undefined)
  const publishing = useRef(false)

  // Publish the mic once, on first connect. Honour a mute pressed while still connecting.
  useEffect(() => {
    if (connection !== ConnectionState.Connected || publishing.current) return
    const [track] = stream.getAudioTracks()
    if (!track) return
    publishing.current = true
    room.localParticipant
      .publishTrack(track, { source: Track.Source.Microphone })
      .then(async (pub) => {
        publication.current = pub
        if (mutedRef.current) await pub.mute()
      })
      .catch(() => onEnd('connection-lost'))
  }, [connection, room, stream, onEnd])

  // The agent (or its avatar) leaving ends the call: at the time limit, or if it failed.
  useEffect(() => {
    const onLeave = (participant: RemoteParticipant) => {
      if (participant.kind !== ParticipantKind.AGENT) return
      onEnd('connection-lost')
    }
    room.on(RoomEvent.ParticipantDisconnected, onLeave)
    return () => {
      room.off(RoomEvent.ParticipantDisconnected, onLeave)
    }
  }, [room, onEnd])

  async function toggleMute() {
    const next = !muted
    mutedRef.current = next
    setMuted(next)
    const pub = publication.current
    if (pub) await (next ? pub.mute() : pub.unmute())
    else stream.getAudioTracks().forEach((t) => (t.enabled = !next))
  }

  const transcript: Turn[] = transcriptions
    .filter((t) => t.text.trim())
    .map((t) => ({
      id: t.streamInfo.id,
      speaker: t.participantInfo.identity === localParticipant.identity ? 'You' : AGENT_LABEL,
      text: t.text,
    }))

  let status: string | undefined
  if (connection === ConnectionState.Connecting) status = 'Connecting…'
  else if (connection === ConnectionState.Reconnecting) status = 'Connection unsteady. Reconnecting…'
  else if (!videoTrack && !voiceOnly) status = "Waiting for Lee's avatar to join…"

  return (
    <>
      <RoomAudioRenderer />
      <CallLayout
        video={
          videoTrack ? (
            <VideoTrack trackRef={videoTrack} className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
              {voiceOnly && !status ? (
                <>
                  {/* Moves with the agent's voice and state, so the call still feels alive. */}
                  <AgentAudioVisualizerAura
                    size="lg"
                    state={agentState}
                    audioTrack={audioTrack}
                    themeMode="light"
                    className="max-h-[70%]"
                    aria-hidden
                  />
                  <span className="text-sm">Voice only</span>
                </>
              ) : (
                status
              )}
            </div>
          )
        }
        status={videoTrack || voiceOnly ? status : undefined}
        notices={notices}
        audioPrompt={
          // Shown only if the browser blocked autoplay.
          <StartAudio label="Turn on the avatar's sound" className="rounded-md border px-3 py-1.5 text-sm" />
        }
        transcript={transcript}
        muted={muted}
        onToggleMute={toggleMute}
        onEnd={onEnd}
      />
    </>
  )
}

// Placeholder transcript for preview. The live call shows LiveKit's transcription instead.
const PREVIEW_TRANSCRIPT: Turn[] = [
  { id: 'greeting', speaker: AGENT_LABEL, text: "Hi, I'm an AI avatar of Lee, not the real person. What would you like to know?" },
]

function PreviewCall({
  stream,
  failConnection,
  onEnd,
}: {
  stream: MediaStream
  failConnection: boolean
  onEnd: (end: CallEnd) => void
}) {
  const [muted, setMuted] = useState(false)

  useEffect(() => {
    if (!failConnection) return
    const id = setTimeout(() => onEnd('connection-lost'), 5000)
    return () => clearTimeout(id)
  }, [failConnection, onEnd])

  function toggleMute() {
    const next = !muted
    stream.getAudioTracks().forEach((t) => (t.enabled = !next))
    setMuted(next)
  }

  return (
    <CallLayout
      video={<div className="flex h-full items-center justify-center text-muted-foreground">Avatar video</div>}
      transcript={PREVIEW_TRANSCRIPT}
      muted={muted}
      onToggleMute={toggleMute}
      onEnd={onEnd}
    />
  )
}

function CallLayout({
  video,
  status,
  notices = [],
  audioPrompt,
  transcript,
  muted,
  onToggleMute,
  onEnd,
}: {
  video: ReactNode
  status?: string
  /** Provider problems the visitor should know about, from the agent. */
  notices?: string[]
  audioPrompt?: ReactNode
  transcript: Turn[]
  muted: boolean
  onToggleMute: () => void
  onEnd: (end: CallEnd) => void
}) {
  const [secondsLeft, setSecondsLeft] = useState(LIMIT_SECONDS)
  const transcriptEnd = useRef<HTMLDivElement>(null)

  // Display only: the agent ends the call at the limit, and the browser can't extend it (ADR-5).
  useEffect(() => {
    const startedAt = Date.now()
    const id = setInterval(() => {
      const left = Math.max(0, LIMIT_SECONDS - Math.floor((Date.now() - startedAt) / 1000))
      setSecondsLeft(left)
      if (left === 0) onEnd('time-limit')
    }, 1000)
    return () => clearInterval(id)
  }, [onEnd])

  const lastText = transcript.at(-1)?.text
  useEffect(() => {
    transcriptEnd.current?.scrollIntoView({ block: 'nearest' })
  }, [transcript.length, lastText])

  const warning = secondsLeft <= END_WARNING_MINUTES * 60

  return (
    <VisitorPage wide>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <section className="flex flex-col gap-4" aria-label="Call">
          <div className="relative aspect-video overflow-hidden rounded-2xl border bg-muted">
            {video}
            {/* The AI label is permanent and can't be dismissed (ADR-11, I6). */}
            <p className="absolute top-3 left-3 rounded-md bg-foreground px-2.5 py-1 text-sm font-semibold text-background">
              AI avatar of Lee, not the real person
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="flex items-center gap-2 text-sm" role="status">
              <span className="size-2.5 rounded-full bg-destructive" aria-hidden />
              Transcript being saved
            </p>
            {status && (
              <p className="text-sm text-muted-foreground" role="status">
                {status}
              </p>
            )}
            <p className="text-sm text-muted-foreground tabular-nums" aria-live="off">
              {formatClock(secondsLeft)} left
            </p>
          </div>

          {notices.map((notice) => (
            <p key={notice} role="status" className="rounded-lg border bg-muted px-4 py-3 text-sm">
              {notice}
            </p>
          ))}

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
              onClick={onToggleMute}
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
            {audioPrompt}
          </div>
        </section>

        <aside className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Transcript</CardTitle>
            </CardHeader>
            <CardContent className="flex max-h-80 flex-col gap-3 overflow-y-auto text-sm" aria-live="polite">
              {transcript.length === 0 && <p className="text-muted-foreground">The conversation appears here.</p>}
              {transcript.map((turn) => (
                <p key={turn.id}>
                  <span className="font-semibold">{turn.speaker}: </span>
                  {turn.text}
                </p>
              ))}
              <div ref={transcriptEnd} />
            </CardContent>
          </Card>
        </aside>
      </div>
    </VisitorPage>
  )
}


