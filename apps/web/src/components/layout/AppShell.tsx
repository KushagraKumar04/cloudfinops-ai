import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

export function AppShell() {
  return (
    <div className="flex min-h-screen bg-canvas">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded focus:border focus:border-border focus:bg-surface focus:px-3 focus:py-1.5 focus:text-sm focus:text-ink focus:shadow-sm"
      >
        Skip to content
      </a>
      <Sidebar />
      <div className="flex flex-1 flex-col min-w-0">
        <Topbar />
        <main id="main-content" className="flex-1 px-4 sm:px-6 lg:px-8 py-6" tabIndex={-1}>
          <div className="mx-auto w-full max-w-[1200px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}