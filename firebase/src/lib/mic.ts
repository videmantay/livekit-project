// Microphone access. Nothing here prompts except requestMic, which runs only after consent (ADR-4).

export type MicProblem = 'insecure' | 'blocked' | 'no-device' | 'busy' | 'unknown'

/**
 * Problems we can spot before a session is spent, without prompting. A blocked mic fails at once,
 * with no prompt, so it is worth catching before POST /sessions.
 */
export async function precheckMic(): Promise<MicProblem | undefined> {
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) return 'insecure'
  try {
    const status = await navigator.permissions.query({ name: 'microphone' as PermissionName })
    if (status.state === 'denied') return 'blocked'
  } catch {
    // Some browsers can't query the mic permission. The real request will tell us.
  }
  return undefined
}

export async function requestMic(): Promise<MediaStream | MicProblem> {
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) return 'insecure'
  try {
    return await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch (err) {
    const name = err instanceof DOMException ? err.name : ''
    if (name === 'NotAllowedError' || name === 'SecurityError') return 'blocked'
    if (name === 'NotFoundError' || name === 'OverconstrainedError') return 'no-device'
    if (name === 'NotReadableError' || name === 'AbortError') return 'busy'
    return 'unknown'
  }
}

export const MIC_PROBLEM_TEXT: Record<MicProblem, string> = {
  insecure: "This page can't use a microphone because it isn't on a secure (https) address.",
  blocked:
    'Your browser is blocking the microphone for this site. Click the icon next to the address bar, set Microphone to Allow, then try again.',
  'no-device': "We couldn't find a microphone. Plug one in or turn it on, then try again.",
  busy: 'Your microphone is in use by another app or tab. Close it, then try again.',
  unknown: "Your browser couldn't start the microphone. Check its settings, then try again.",
}
