// Admin API. Real calls go to cloud-run with a Google ID token (ADR-10).
// With admin sign-in configured, every call goes to cloud-run. Without it, the whole admin
// area uses the in-memory mock below, for local preview. The two are never mixed.

import { adminAuthConfigured, adminIdToken } from './admin-auth'

/** `violation` marks a turn the agent counted as inappropriate (I8). */
export type TranscriptTurn = { speaker: 'visitor' | 'agent'; text: string; violation?: boolean }

/** `created`: a token was issued but no transcript has arrived. `active`: in progress. */
export type SessionStatus = 'created' | 'active' | 'ended'

/** Null until the call ends. `empty`: nothing was said. `failed`: the model call failed. */
export type SummaryStatus = 'done' | 'empty' | 'failed' | null

export type Conversation = {
  id: string
  inviteLabel: string
  startedAt: string
  durationSeconds: number
  status: SessionStatus
  /** Null if the agent never sent a transcript batch. */
  factsVersion: number | null
  summary: string
  summaryStatus: SummaryStatus
  declinedQuestions: string[]
  transcript: TranscriptTurn[]
  contact?: { name?: string; email?: string; company?: string }
}

export type Invite = {
  id: string
  label: string
  sessionLimit: number
  sessionsUsed: number
  expiresAt: string
  revoked: boolean
}

// Prompt order in the agent. Matches cloud-run's facts.SECTIONS.
export const FACT_SECTIONS = {
  profile: 'Profile',
  experience: 'Experience',
  skills: 'Skills',
  spoken_languages: 'Spoken languages',
  education: 'Education',
  not_skills: "Skills Lee doesn't have",
} as const

export type FactSection = keyof typeof FACT_SECTIONS

/** A STAR story the avatar tells, in this order, when asked for an example. */
export type Story = { title: string; situation: string; task: string; action: string; result: string }

export type Fact = {
  id: string
  section: FactSection
  topic: string
  level: string
  verified: string
  limits: string
  stories: Story[]
}

export type FactsVersion = { number: number; publishedAt: string; facts: Fact[] }

export type FactsState = { working: Fact[]; versions: FactsVersion[] }

export interface AdminApi {
  listConversations(): Promise<Conversation[]>
  /** Deletes the session, transcript, summary and contact details together (A7). */
  deleteConversation(id: string): Promise<void>
  listInvites(): Promise<Invite[]>
  /** Returns the code once. It can't be fetched again (A1). */
  createInvite(input: { label: string; sessionLimit: number; expiresInDays: number }): Promise<{
    invite: Invite
    code: string
  }>
  revokeInvite(id: string): Promise<Invite>
  getFacts(): Promise<FactsState>
  saveFact(fact: Fact): Promise<FactsState>
  deleteFact(id: string): Promise<FactsState>
  publishFacts(): Promise<FactsState>
  rollbackFacts(versionNumber: number): Promise<FactsState>
}

const wait = (ms = 250) => new Promise((resolve) => setTimeout(resolve, ms))
const daysFromNow = (days: number) => new Date(Date.now() + days * 86_400_000).toISOString()
const clone = <T>(value: T): T => structuredClone(value)

let conversations: Conversation[] = [
  {
    id: 's1',
    inviteLabel: 'Sample: platform team recruiter',
    startedAt: daysFromNow(-1),
    durationSeconds: 11 * 60 + 42,
    status: 'ended',
    summaryStatus: 'done',
    factsVersion: 2,
    summary:
      'Asked about full-stack work and AI integration, then about on-site deployment. Wanted to know about Kubernetes in production, which the avatar declined.',
    declinedQuestions: ['Have you run Kubernetes clusters in production?'],
    transcript: [
      { speaker: 'agent', text: "Hi, I'm an AI avatar of Lee, not the real person. What would you like to know?" },
      { speaker: 'visitor', text: 'What does Lee work on day to day?' },
      { speaker: 'agent', text: 'Lee is a senior software engineer doing full-stack work and AI integration.' },
      { speaker: 'visitor', text: 'Have you run Kubernetes clusters in production?' },
      { speaker: 'agent', text: "That isn't something I can speak to. Please ask Lee directly." },
    ],
    contact: { name: 'Sample Person', email: 'sample@example.com', company: 'Example Co' },
  },
  {
    id: 's2',
    inviteLabel: 'Sample: startup founder',
    startedAt: daysFromNow(-3),
    durationSeconds: 4 * 60 + 5,
    status: 'ended',
    summaryStatus: 'done',
    factsVersion: 1,
    summary: 'Short call about travel and customer-facing work. No contact details left.',
    declinedQuestions: [],
    transcript: [
      { speaker: 'agent', text: "Hi, I'm an AI avatar of Lee, not the real person. What would you like to know?" },
      { speaker: 'visitor', text: 'Is Lee open to travel?' },
      { speaker: 'agent', text: 'Yes, Lee is open to travel and on-site customer deployment.' },
    ],
  },
]

let invites: Invite[] = [
  { id: 'i1', label: 'Sample: platform team recruiter', sessionLimit: 2, sessionsUsed: 1, expiresAt: daysFromNow(10), revoked: false },
  { id: 'i2', label: 'Sample: startup founder', sessionLimit: 2, sessionsUsed: 2, expiresAt: daysFromNow(4), revoked: false },
  { id: 'i3', label: 'Sample: old invite', sessionLimit: 2, sessionsUsed: 0, expiresAt: daysFromNow(-2), revoked: true },
]

const seedFacts: Fact[] = [
  {
    id: 'f1',
    section: 'profile',
    topic: 'Current role and focus',
    level: 'Senior',
    verified: 'Senior software engineer doing full-stack work and AI integration.',
    limits: "Don't discuss availability, start dates, pay or offers. Send those to Lee.",
    stories: [],
  },
  {
    id: 'f2',
    section: 'profile',
    topic: 'Travel',
    level: 'Yes',
    verified: 'Open to travel and on-site customer deployment.',
    limits: 'No specific dates or locations.',
    stories: [
      {
        title: 'Sample story',
        situation: 'Sample situation.',
        task: 'Sample task.',
        action: 'Sample action.',
        result: 'Sample result, with a number Lee confirmed.',
      },
    ],
  },
]

let facts: FactsState = {
  working: clone(seedFacts),
  versions: [
    { number: 1, publishedAt: daysFromNow(-5), facts: clone(seedFacts.slice(0, 1)) },
    { number: 2, publishedAt: daysFromNow(-2), facts: clone(seedFacts) },
  ],
}

let nextId = 100
const newId = (prefix: string) => `${prefix}${nextId++}`

function randomCode() {
  // 144 bits, like cloud-run's codes. The real one is generated server-side.
  const bytes = crypto.getRandomValues(new Uint8Array(18))
  return btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_')
}

function publish(working: Fact[]): FactsState {
  const number = (facts.versions.at(-1)?.number ?? 0) + 1
  facts = {
    working: clone(working),
    versions: [...facts.versions, { number, publishedAt: new Date().toISOString(), facts: clone(working) }],
  }
  return clone(facts)
}

export const mockAdminApi: AdminApi = {
  async listConversations() {
    await wait()
    return clone(conversations)
  },
  async deleteConversation(id) {
    await wait()
    conversations = conversations.filter((c) => c.id !== id)
  },
  async listInvites() {
    await wait()
    return clone(invites)
  },
  async createInvite({ label, sessionLimit, expiresInDays }) {
    await wait()
    const invite: Invite = {
      id: newId('i'),
      label,
      sessionLimit,
      sessionsUsed: 0,
      expiresAt: daysFromNow(expiresInDays),
      revoked: false,
    }
    invites = [invite, ...invites]
    return { invite: clone(invite), code: randomCode() }
  },
  async revokeInvite(id) {
    await wait()
    invites = invites.map((i) => (i.id === id ? { ...i, revoked: true } : i))
    return clone(invites.find((i) => i.id === id)!)
  },
  async getFacts() {
    await wait()
    return clone(facts)
  },
  async saveFact(fact) {
    await wait()
    const exists = facts.working.some((f) => f.id === fact.id)
    const saved = fact.id ? fact : { ...fact, id: newId('f') }
    facts = {
      ...facts,
      working: exists
        ? facts.working.map((f) => (f.id === fact.id ? clone(saved) : f))
        : [...facts.working, clone(saved)],
    }
    return clone(facts)
  },
  async deleteFact(id) {
    await wait()
    facts = { ...facts, working: facts.working.filter((f) => f.id !== id) }
    return clone(facts)
  },
  async publishFacts() {
    await wait()
    return publish(facts.working)
  },
  async rollbackFacts(versionNumber) {
    await wait()
    const version = facts.versions.find((v) => v.number === versionNumber)
    if (!version) throw new Error('No such version')
    return publish(version.facts)
  },
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class AdminApiError extends Error {
  readonly status: number
  constructor(status: number) {
    super(status === 401 ? 'Not signed in as admin' : `Request failed with ${status}`)
    this.status = status
  }
}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${await adminIdToken()}`,
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) throw new AdminApiError(response.status)
  // DELETE /admin/conversations/{id} answers 204 with no body.
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

const factBody = ({ id: _id, ...fact }: Fact) => fact

/** Facts on cloud-run (ADR-21). Every call sends the ID token, which cloud-run checks. */
export const cloudRunFactsApi: Pick<AdminApi, 'getFacts' | 'saveFact' | 'deleteFact' | 'publishFacts' | 'rollbackFacts'> =
  {
    getFacts: () => call('GET', '/admin/facts'),
    saveFact: (fact) =>
      fact.id
        ? call('PUT', `/admin/facts/${encodeURIComponent(fact.id)}`, factBody(fact))
        : call('POST', '/admin/facts', factBody(fact)),
    deleteFact: (id) => call('DELETE', `/admin/facts/${encodeURIComponent(id)}`),
    publishFacts: () => call('POST', '/admin/facts/publish'),
    rollbackFacts: (version) => call('POST', '/admin/facts/rollback', { version }),
  }

/** Invites on cloud-run (A1, A7). The code is in the create response only, never stored (ADR-3). */
export const cloudRunInvitesApi: Pick<AdminApi, 'listInvites' | 'createInvite' | 'revokeInvite'> = {
  listInvites: () => call('GET', '/admin/invites'),
  createInvite: (input) => call('POST', '/admin/invites', input),
  revokeInvite: (id) => call('POST', `/admin/invites/${encodeURIComponent(id)}/revoke`),
}

/** Conversations on cloud-run (A6, A7). Newest first, at most 100. */
export const cloudRunConversationsApi: Pick<AdminApi, 'listConversations' | 'deleteConversation'> = {
  listConversations: () => call('GET', '/admin/conversations'),
  deleteConversation: (id) => call('DELETE', `/admin/conversations/${encodeURIComponent(id)}`),
}

// Spelled out rather than spread over the mock, so a new AdminApi method that has no real
// version fails the type check instead of quietly using fake data.
export const adminApi: AdminApi = adminAuthConfigured
  ? { ...cloudRunFactsApi, ...cloudRunInvitesApi, ...cloudRunConversationsApi }
  : mockAdminApi
