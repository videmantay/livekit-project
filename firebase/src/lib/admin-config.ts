// Admin sign-in config, kept apart from admin-auth.ts so the visitor bundle can read the flag
// without loading the firebase package. Every VITE_ value is public.

export const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

/** Without it, the whole admin area runs on the in-memory mock, for local preview. */
export const adminAuthConfigured = Boolean(firebaseConfig.apiKey && firebaseConfig.authDomain && firebaseConfig.projectId)
