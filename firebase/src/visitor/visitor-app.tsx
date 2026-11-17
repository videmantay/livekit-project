import { lazy, Suspense, useState } from 'react'
import { ApiError, visitorApi, visitorPreview, type Contact, type SessionGrant, type Terms } from '@/lib/api'
import { takeInviteCode } from '@/lib/invite-link'
import { MIC_PROBLEM_TEXT, precheckMic, requestMic, type MicProblem } from '@/lib/mic'
import type { CallEnd } from './call-screen'
import { ContactScreen } from './contact-screen'
import { EndScreen, type EndReason } from './end-screen'
import { GateScreen } from './gate-screen'
import { BUSY_ERROR, GENERIC_CODE_ERROR, RATE_LIMIT_ERROR, START_ERROR } from './messages'
import { MicScreen } from './mic-screen'
import { TermsScreen } from './terms-screen'

// LiveKit is large, so it loads only once a call starts, not on the gate or the portfolio.
const CallScreen = lazy(() => import('./call-screen').then((m) => ({ default: m.CallScreen })))

// Order is fixed by ADR-4: valid code, then terms, then POST /sessions, then the mic.
type Step =
  | { name: 'gate'; error?: string }
  | { name: 'terms'; code: string; terms: Terms; notice?: string }
  | { name: 'contact'; code: string; terms: Terms }
  | { name: 'mic'; grant: SessionGrant; problem: MicProblem; failConnection: boolean }
  | { name: 'call'; grant: SessionGrant; stream: MediaStream; failConnection: boolean }
  | { name: 'ended'; reason: EndReason }

// A 503 means the invite was busy and nothing was used, so one automatic retry is safe.
// The wait is capped so a large Retry-After can't leave the visitor staring at a spinner.
const MAX_RETRY_WAIT_SECONDS = 5

async function startSessionWithRetry(input: Parameters<typeof visitorApi.startSession>[0]) {
  try {
    return await visitorApi.startSession(input)
  } catch (err) {
    if (!(err instanceof ApiError && err.status === 503)) throw err
    const seconds = Math.min(err.retryAfter ?? 1, MAX_RETRY_WAIT_SECONDS)
    await new Promise((resolve) => setTimeout(resolve, seconds * 1000))
    return visitorApi.startSession(input)
  }
}

export function VisitorApp() {
  const [step, setStep] = useState<Step>({ name: 'gate' })

  async function startCall(code: string, terms: Terms, contact: Contact | undefined): Promise<string | undefined> {
    // Catch a mic that can't work before spending a session. This doesn't prompt (ADR-4).
    const problem = await precheckMic()
    if (problem) return MIC_PROBLEM_TEXT[problem]

    let grant: SessionGrant
    try {
      grant = await startSessionWithRetry({ code, termsVersion: terms.version, contact })
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // Terms changed since the page loaded: fetch the current ones and ask again (I3).
        try {
          const fresh = await visitorApi.verifyInvite(code)
          setStep({
            name: 'terms',
            code,
            terms: fresh,
            notice: 'The terms have changed since you opened this page. Please read them again.',
          })
        } catch {
          setStep({ name: 'gate', error: GENERIC_CODE_ERROR })
        }
        return
      }
      if (err instanceof ApiError && err.status === 403) {
        setStep({ name: 'gate', error: GENERIC_CODE_ERROR })
        return
      }
      if (err instanceof ApiError && err.status === 429) return RATE_LIMIT_ERROR
      if (err instanceof ApiError && err.status === 503) return BUSY_ERROR
      return START_ERROR
    }

    // The session is spent from here on, so a refused mic still uses it (ADR-4). The visitor
    // can retry the mic against the same grant without spending another.
    const failConnection = visitorPreview && code === 'drop'
    const result = await requestMic()
    if (result instanceof MediaStream) setStep({ name: 'call', grant, stream: result, failConnection })
    else setStep({ name: 'mic', grant, problem: result, failConnection })
  }

  function endCall(stream: MediaStream, end: CallEnd) {
    stream.getTracks().forEach((t) => t.stop())
    setStep({ name: 'ended', reason: end })
  }

  switch (step.name) {
    case 'gate':
      return (
        <GateScreen
          initialError={step.error}
          linkCode={takeInviteCode()}
          onVerified={(code, terms) => setStep({ name: 'terms', code, terms })}
        />
      )
    case 'terms':
      return (
        <TermsScreen
          terms={step.terms}
          notice={step.notice}
          onAccept={() => setStep({ name: 'contact', code: step.code, terms: step.terms })}
        />
      )
    case 'contact':
      return (
        <ContactScreen
          onBack={() => setStep({ name: 'terms', code: step.code, terms: step.terms })}
          onStart={(contact) => startCall(step.code, step.terms, contact)}
        />
      )
    case 'mic':
      return (
        <MicScreen
          problem={step.problem}
          onGranted={(stream) =>
            setStep({ name: 'call', grant: step.grant, stream, failConnection: step.failConnection })
          }
          onGiveUp={() => setStep({ name: 'ended', reason: 'mic-denied' })}
        />
      )
    case 'call':
      return (
        <Suspense fallback={null}>
          <CallScreen
            grant={step.grant}
            stream={step.stream}
            preview={visitorPreview}
            failConnection={step.failConnection}
            onEnd={(end) => endCall(step.stream, end)}
          />
        </Suspense>
      )
    case 'ended':
      return <EndScreen reason={step.reason} />
  }
}
