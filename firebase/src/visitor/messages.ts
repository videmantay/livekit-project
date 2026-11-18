// One message for every bad code, so nobody can tell an expired code from a wrong one (U1).
export const GENERIC_CODE_ERROR = "That code doesn't work. Check your invitation, or contact Lee for a new one."
export const RATE_LIMIT_ERROR = 'Too many attempts. Please wait a minute, then try again.'
// 503 from POST /sessions: contention on the invite. Nothing was used, so retrying is safe (I9).
export const BUSY_ERROR = 'The line is busy right now. No session was used, so you can safely try again.'
export const START_ERROR = "We couldn't start the call. Please try again in a minute."

// Shown during a call when a provider fails partway and the agent carries on without it (I7).
export const SERVICE_NOTICES = {
  videoUnavailable:
    'Video is temporarily unavailable because of an issue with one of our service providers. The conversation continues with voice only.',
  backupVoice:
    "Lee's usual voice is temporarily unavailable because of an issue with one of our service providers. A standard voice is speaking for now.",
} as const
