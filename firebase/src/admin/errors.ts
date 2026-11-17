import { AdminApiError } from '@/lib/admin-api'

/** What to show when an admin request fails. The server's reason is never shown (ADR-14). */
export function errorText(error: unknown) {
  if (error instanceof AdminApiError && error.status === 401) {
    return "Your sign-in was refused. Sign out and back in with Lee's account."
  }
  return "That didn't work. Check the connection and try again."
}
