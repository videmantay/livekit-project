// Public settings only. Every VITE_ value ends up in the browser bundle.

export const LINKEDIN_URL = import.meta.env.VITE_LINKEDIN_URL || 'https://www.linkedin.com/'

// Must match cloud-run and the agent. The agent enforces it; the browser only shows it (ADR-5).
export const MAX_SESSION_MINUTES = 15
export const END_WARNING_MINUTES = 2

// Static clip of Lee speaking Portuguese (ADR-20). Shows a placeholder until the file exists.
export const PORTUGUESE_CLIP_URL = '/lee-portuguese.mp3'
