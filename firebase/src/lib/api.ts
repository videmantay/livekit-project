// Visitor API. The shapes follow cloud-run's endpoints, with the terms coming
// back from verify as ADR-15 requires.
//
// With VITE_API_URL set, requests go to cloud-run. Without it, the in-memory mock below
// stands in, for local preview.

import { isTermsLanguage, type TermsLanguage } from './terms-language'

/** `offered` lists the languages cloud-run offers now, so the screen knows whether to show a switch. */
export type Terms = { version: string; text: string; language: TermsLanguage; offered: TermsLanguage[] }

export type Contact = { name?: string; email?: string; company?: string }

export type SessionGrant = { room: string; token: string; url: string }

export class ApiError extends Error {
  readonly status: number
  /** Seconds from the Retry-After header, when the server sent one. */
  readonly retryAfter?: number
  constructor(status: number, retryAfter?: number) {
    super(`Request failed with ${status}`)
    this.status = status
    this.retryAfter = retryAfter
  }
}

function parseRetryAfter(header: string | null): number | undefined {
  if (header === null) return undefined
  const seconds = Number(header)
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : undefined
}

export interface VisitorApi {
  /**
   * POST /invites/verify. Doesn't use a session. 403 or 429 on failure. A language cloud-run
   * doesn't offer comes back as English.
   */
  verifyInvite(code: string, language: TermsLanguage): Promise<Terms>
  /**
   * POST /sessions. Uses one session. 403, 409 (terms changed) or 429 on failure, or 503
   * with Retry-After when the invite is busy, in which case nothing was used.
   */
  startSession(input: {
    code: string
    termsVersion: string
    termsLanguage: TermsLanguage
    contact?: Contact
  }): Promise<SessionGrant>
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const MOCK_TERMS_TEXT_EN = `# Before you start

This conversation is with an AI avatar of Lee. It is not the real person.

**The avatar speaks for itself, not for Lee.** It can make mistakes. Nothing it says is a statement, promise, or agreement from Lee, including anything about pay, availability, or an offer. Please confirm anything important with Lee directly.

**This conversation is saved.** Your speech is converted to text. The transcript and any contact details you give are stored, summarized by AI, and reviewed by Lee. No audio or video of you is saved by this site.

**Other companies process this conversation** so the avatar can work, each under its own terms: LiveKit (real-time connection) and AssemblyAI (speech-to-text) receive your speech, Google (AI responses and data storage) receives the transcript, and ElevenLabs (the avatar's voice) and Tavus (the avatar's video) receive only the avatar's replies.

**Your data is deleted after 90 days.** To have it deleted sooner, email the address in the real terms.

**Please do not share confidential or sensitive information.**

**Please do not record, copy, or reuse the avatar, its voice, or its likeness.**

By continuing, you confirm that you have read this and agree to your conversation being transcribed, stored, and reviewed as described above.

_Preview text. The real terms come from cloud-run._`

// Short on purpose: the preview only needs to show the switch. The draft is cloud-run's terms.es.md.
const MOCK_TERMS_TEXT_ES = `# Antes de empezar

Esta conversación es con un avatar de IA de Lee. No es la persona real.

**Esta conversación se guarda.** Su voz se convierte en texto. La transcripción y los datos de contacto que proporcione se almacenan, se resumen con IA y los revisa Lee.

_Texto de vista previa. Las condiciones reales vienen de cloud-run._`

const MOCK_TERMS_TEXT: Record<TermsLanguage, string> = { en: MOCK_TERMS_TEXT_EN, es: MOCK_TERMS_TEXT_ES }

let mockTermsVersion = 'preview-1'

/**
 * In-memory stand-in for cloud-run. Any code works, except these, which act out failures:
 * - `bad`: 403 at the gate
 * - `slow`: 429 at the gate
 * - `stale`: 409 on the first start, as if the terms changed after the page loaded
 * - `used`: valid at the gate, then 403 on start (sessions used up)
 * - `busy`: 503 on the first start, then it works, as if the automatic retry got through
 * - `jammed`: 503 on every start, so the busy message shows
 * - `drop`: the call connects, then the connection is lost
 */
let mockBusyOnce = true
export const mockVisitorApi: VisitorApi = {
  async verifyInvite(code, language) {
    await wait(400)
    if (code === 'bad') throw new ApiError(403)
    if (code === 'slow') throw new ApiError(429)
    // The preview offers Spanish so the switch can be tried; cloud-run doesn't until it's reviewed.
    return {
      version: `${mockTermsVersion}-${language}`,
      text: MOCK_TERMS_TEXT[language],
      language,
      offered: ['en', 'es'],
    }
  },
  async startSession({ code, termsVersion, termsLanguage }) {
    await wait(600)
    if (code === 'used') throw new ApiError(403)
    if (code === 'jammed') throw new ApiError(503, 1)
    if (code === 'busy' && mockBusyOnce) {
      mockBusyOnce = false
      throw new ApiError(503, 1)
    }
    if (code === 'stale' && mockTermsVersion === 'preview-1') {
      mockTermsVersion = 'preview-2'
      throw new ApiError(409)
    }
    if (termsVersion !== `${mockTermsVersion}-${termsLanguage}`) throw new ApiError(409)
    return { room: `mock-${code}`, token: 'mock-token', url: 'wss://mock.invalid' }
  },
}

const API_URL = import.meta.env.VITE_API_URL as string | undefined

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new ApiError(response.status, parseRetryAfter(response.headers.get('Retry-After')))
  }
  return response.json() as Promise<T>
}

export const cloudRunVisitorApi: VisitorApi = {
  async verifyInvite(code, language) {
    const { terms, languages } = await post<{
      terms: Omit<Terms, 'offered'>
      languages: unknown[]
    }>('/invites/verify', { code, language })
    // Unknown codes are dropped, so a language added to cloud-run first can't break this build.
    return { ...terms, offered: languages.filter(isTermsLanguage) }
  },
  startSession({ code, termsVersion, termsLanguage, contact }) {
    // The visitor ticked the box to get here; cloud-run refuses a session without it (I2).
    return post('/sessions', {
      code,
      terms_version: termsVersion,
      terms_language: termsLanguage,
      terms_accepted: true,
      contact,
    })
  },
}

/** True when no cloud-run is configured, so every visitor request goes to the mock. */
export const visitorPreview = !API_URL

export const visitorApi: VisitorApi = visitorPreview ? mockVisitorApi : cloudRunVisitorApi
