// Invite links carry the code in the URL fragment: /invite#invite=<code> (ADR-3).
//
// Browsers never send the fragment to a server, so the code stays out of Hosting logs and
// the Referer header (ADR-14). It's read once, kept in memory, and cleared from the address
// bar so it doesn't stay in history or get copied along with the current URL.

const PARAM = 'invite'

let taken = false
let linkCode: string | undefined

/**
 * The code from an invite link, or undefined. The first call clears it from the URL, and
 * later calls return the same value, so React's StrictMode double render is harmless.
 */
export function takeInviteCode(): string | undefined {
  if (taken) return linkCode
  taken = true
  const hash = window.location.hash.replace(/^#/, '')
  if (!hash) return undefined
  const value = new URLSearchParams(hash).get(PARAM)?.trim()
  // Remove the whole fragment, even when it held no code, so nothing stray lingers.
  window.history.replaceState(window.history.state, '', window.location.pathname + window.location.search)
  linkCode = value || undefined
  return linkCode
}

/** The link the admin sends. The code goes in the fragment, never the query string. */
export function inviteLink(code: string, origin = window.location.origin): string {
  return `${origin}/invite#${PARAM}=${encodeURIComponent(code)}`
}

/**
 * A plain-text message to paste into an email. The code sits on its own line so it can be
 * copied cleanly if the link breaks. Move the name to the owner profile with ADR-23.
 */
export function inviteMessage(input: {
  link: string
  code: string
  sessionLimit: number
  expiresOn: string
}): string {
  const sessions = input.sessionLimit === 1 ? 'one conversation' : `${input.sessionLimit} conversations`
  return [
    'Hi,',
    '',
    "You're invited to talk with Lee's AI avatar, a voice and video twin that answers questions about Lee's work and experience.",
    '',
    'Open this link to start:',
    input.link,
    '',
    `If the link doesn't open, go to ${new URL(input.link).origin}/invite and paste this access code:`,
    input.code,
    '',
    `The invitation is good for ${sessions} and expires on ${input.expiresOn}. You'll see the terms before anything starts, and your microphone is only requested after you agree.`,
    '',
    'Please keep the link to yourself. It works only for you.',
    '',
    'Lee',
  ].join('\n')
}
