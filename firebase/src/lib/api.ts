// Visitor API. The shapes follow cloud-run's endpoints, with the terms coming
// back from verify as ADR-15 requires.
//
// With VITE_API_URL set, requests go to cloud-run. Without it, the in-memory mock below
// stands in, for local preview.

export type Terms = { version: string; text: string }

export type Contact = { name?: string; email?: string; company?: string }

export type SessionGrant = { room: string; token: string; url: string }

export class ApiError extends Error {
  readonly status: number
  constructor(status: number) {
    super(`Request failed with ${status}`)
    this.status = status
  }
}

export interface VisitorApi {
  /** POST /invites/verify. Doesn't use a session. 403 or 429 on failure. */
  verifyInvite(code: string): Promise<Terms>
  /** POST /sessions. Uses one session. 403, 409 (terms changed) or 429 on failure. */
  startSession(input: {
    code: string
    termsVersion: string
    contact?: Contact
  }): Promise<SessionGrant>
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const MOCK_TERMS_TEXT = `# Before you start

This conversation is with an AI avatar of Lee. It is not the real person.

**The avatar speaks for itself, not for Lee.** It can make mistakes. Nothing it says is a statement, promise, or agreement from Lee, including anything about pay, availability, or an offer. Please confirm anything important with Lee directly.

**This conversation is saved.** Your speech is converted to text. The transcript and any contact details you give are stored, summarized by AI, and reviewed by Lee. No audio or video of you is saved by this site.

**Other companies process this conversation** so the avatar can work: LiveKit (real-time connection), Tavus (avatar video), ElevenLabs (voice and speech-to-text), and Google (AI responses and data storage).

**Your data is deleted after 90 days.** To have it deleted sooner, email the address in the real terms.

**Please do not share confidential or sensitive information.**

**Please do not record, copy, or reuse the avatar, its voice, or its likeness.**

By continuing, you confirm that you have read this and agree to your conversation being transcribed, stored, and reviewed as described above.

_Preview text. The real terms come from cloud-run._`

let mockTermsVersion = 'preview-1'

/**
 * In-memory stand-in for cloud-run. Any code works, except these, which act out failures:
 * - `bad`: 403 at the gate
 * - `slow`: 429 at the gate
 * - `stale`: 409 on the first start, as if the terms changed after the page loaded
 * - `used`: valid at the gate, then 403 on start (sessions used up)
 * - `drop`: the call connects, then the connection is lost
 */
export const mockVisitorApi: VisitorApi = {
  async verifyInvite(code) {
    await wait(400)
    if (code === 'bad') throw new ApiError(403)
    if (code === 'slow') throw new ApiError(429)
    return { version: mockTermsVersion, text: MOCK_TERMS_TEXT }
  },
  async startSession({ code, termsVersion }) {
    await wait(600)
    if (code === 'used') throw new ApiError(403)
    if (code === 'stale' && mockTermsVersion === 'preview-1') {
      mockTermsVersion = 'preview-2'
      throw new ApiError(409)
    }
    if (termsVersion !== mockTermsVersion) throw new ApiError(409)
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
  if (!response.ok) throw new ApiError(response.status)
  return response.json() as Promise<T>
}

export const cloudRunVisitorApi: VisitorApi = {
  async verifyInvite(code) {
    const { terms } = await post<{ terms: Terms }>('/invites/verify', { code })
    return terms
  },
  startSession({ code, termsVersion, contact }) {
    // The visitor ticked the box to get here; cloud-run refuses a session without it (I2).
    return post('/sessions', { code, terms_version: termsVersion, terms_accepted: true, contact })
  },
}

/** True when no cloud-run is configured, so every visitor request goes to the mock. */
export const visitorPreview = !API_URL

export const visitorApi: VisitorApi = visitorPreview ? mockVisitorApi : cloudRunVisitorApi
