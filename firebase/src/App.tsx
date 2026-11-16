import { lazy, Suspense } from 'react'
import { PreviewBanner } from '@/components/preview-banner'
import { visitorPreview } from '@/lib/api'
import { localeFromPath } from '@/landing/content'
import { LandingPage } from '@/landing/landing-page'
import { VisitorApp } from '@/visitor/visitor-app'

// Loaded only under /admin, so visitors never download the Firebase sign-in code.
const AdminApp = lazy(() => import('@/admin/admin-app').then((m) => ({ default: m.AdminApp })))

// Three areas, so no router: the public portfolio at / (and /es, /pt), the invite flow at
// /invite and the admin pages under /admin. Firebase Hosting rewrites every path to index.html.
export default function App() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/'

  if (path.startsWith('/admin') || path.startsWith('/invite')) {
    // Admin is still mostly mocked, so its banner stays until every page is connected.
    const preview = path.startsWith('/admin') || visitorPreview
    return (
      <div className="flex min-h-svh flex-col">
        {preview && <PreviewBanner />}
        {path.startsWith('/admin') ? (
          <Suspense fallback={null}>
            <AdminApp />
          </Suspense>
        ) : (
          <VisitorApp />
        )}
      </div>
    )
  }
  return <LandingPage locale={localeFromPath(path) ?? 'en'} />
}
