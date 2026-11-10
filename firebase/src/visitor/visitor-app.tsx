import { useState } from 'react'
import { ApiError, visitorApi, type Contact, type SessionGrant, type Terms } from '@/lib/api'
import { CallScreen, type CallEnd } from './call-screen'
import { ContactScreen } from './contact-screen'
import { EndScreen, type EndReason } from './end-screen'
import { GateScreen } from './gate-screen'
import { GENERIC_CODE_ERROR, RATE_LIMIT_ERROR, START_ERROR } from './messages'
import { TermsScreen } from './terms-screen'

// Order is fixed by ADR-4: valid code, then terms, then POST /sessions, then the mic.
type Step =
  | { name: 'gate'; error?: string }
  | { name: 'terms'; code: string; terms: Terms; notice?: string }
  | { name: 'contact'; code: string; terms: Terms }
  | { name: 'call'; grant: SessionGrant; stream: MediaStream; failConnection: boolean }
  | { name: 'ended'; reason: EndReason }


export function VisitorApp() {
  const [step, setStep] = useState<Step>({ name: 'gate' })

  async function startCall(code: string, terms: Terms, contact: Contact | undefined): Promise<string | undefined> {
    let grant: SessionGrant
    try {
      grant = await visitorApi.startSession({ code, termsVersion: terms.version, contact })
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
      return START_ERROR
    }

    // The session is spent from here on, so a refused mic still uses it (ADR-4).
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setStep({ name: 'ended', reason: 'mic-denied' })
      return
    }
    setStep({ name: 'call', grant, stream, failConnection: code === 'drop' })
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
    case 'call':
      return (
        <CallScreen
          stream={step.stream}
          failConnection={step.failConnection}
          onEnd={(end) => endCall(step.stream, end)}
        />
      )
    case 'ended':
      return <EndScreen reason={step.reason} />
  }
}
