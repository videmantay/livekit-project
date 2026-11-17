// Admin Google sign-in (ADR-10, A3). The firebase package is used for this only; the browser
// never reads or writes Firestore (ADR-2). cloud-run checks the ID token and the one allowed
// account on every request, so this sign-in alone grants nothing.
//
// Without the VITE_FIREBASE_* config, admin runs on the in-memory mock, for local preview.

import { initializeApp } from 'firebase/app'
import { GoogleAuthProvider, getAuth, onAuthStateChanged, signInWithPopup, signOut, type Auth } from 'firebase/auth'
import { adminAuthConfigured, firebaseConfig as config } from './admin-config'

export { adminAuthConfigured }

let auth: Auth | undefined
function getAdminAuth(): Auth {
  auth ??= getAuth(initializeApp(config))
  return auth
}

export function onAdminChange(callback: (signedIn: boolean) => void): () => void {
  return onAuthStateChanged(getAdminAuth(), (user) => callback(user !== null))
}

export async function signInAdmin(): Promise<void> {
  const provider = new GoogleAuthProvider()
  provider.setCustomParameters({ prompt: 'select_account' })
  await signInWithPopup(getAdminAuth(), provider)
}

export function signOutAdmin(): Promise<void> {
  return signOut(getAdminAuth())
}

/** A fresh ID token for cloud-run. Firebase refreshes it when it's close to expiry. */
export async function adminIdToken(): Promise<string> {
  const user = getAdminAuth().currentUser
  if (!user) throw new Error('Not signed in')
  return user.getIdToken()
}
