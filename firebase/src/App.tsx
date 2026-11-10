import { PreviewBanner } from '@/components/preview-banner'
import { AdminApp } from '@/admin/admin-app'
import { LandingPage } from '@/landing/landing-page'
import { VisitorApp } from '@/visitor/visitor-app'

// Three areas, so no router: the public portfolio at /, the invite flow at /invite and
// the admin pages under /admin. Firebase Hosting rewrites every path to index.html.
export default function App() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/'

  if (path.startsWith('/admin') || path.startsWith('/invite')) {
    return (
      <div className="flex min-h-svh flex-col">
        <PreviewBanner />
        {path.startsWith('/admin') ? <AdminApp /> : <VisitorApp />}
      </div>
    )
  }
  return <LandingPage />
}
