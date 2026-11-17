// Public settings only. Every VITE_ value ends up in the browser bundle.

export const LINKEDIN_URL = import.meta.env.VITE_LINKEDIN_URL || 'https://www.linkedin.com/'

// Lee's personal channel. Its handle carries the legal name, so it comes from config. Empty hides the link.
export const YOUTUBE_URL: string = import.meta.env.VITE_YOUTUBE_URL || ''

// Lee's GitHub profile. Empty hides the link.
export const GITHUB_URL: string = import.meta.env.VITE_GITHUB_URL || ''

// Must match cloud-run and the agent. The agent enforces it; the browser only shows it (ADR-5).
export const MAX_SESSION_MINUTES = 6
export const END_WARNING_MINUTES = 2

// Static clip of Lee speaking Portuguese (ADR-20). Shows a placeholder until the file exists.
export const PORTUGUESE_CLIP_URL = '/lee-portuguese.mp3'
