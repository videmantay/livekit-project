// Admin API. Real calls will go to cloud-run with a Google ID token (ADR-10).
// Only an in-memory mock with sample data exists for now.

export type TranscriptTurn = { speaker: 'visitor' | 'agent'; text: string }

export type Conversation = {
  id: string
  inviteLabel: string
  startedAt: string
  durationSeconds: number
  factsVersion: number
  summary: string
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

export type Fact = {
  id: string
  topic: string
  level: string
  verified: string
  limits: string
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
    topic: 'Current role and focus',
    level: 'Senior',
    verified: 'Senior software engineer doing full-stack work and AI integration.',
    limits: "Don't discuss availability, start dates, pay or offers. Send those to Lee.",
  },
  {
    id: 'f2',
    topic: 'Travel',
    level: 'Yes',
    verified: 'Open to travel and on-site customer deployment.',
    limits: 'No specific dates or locations.',
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

export const adminApi: AdminApi = mockAdminApi
