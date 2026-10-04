import { useState } from 'react'
import { Search, LogOut, User as UserIcon } from 'lucide-react'
import { USE_MOCKS } from '@/lib/api/client'
import { useAuth } from '@/features/auth/useAuth'
import { clsx } from 'clsx'
import { NotificationBell } from './NotificationBell'

export function Topbar() {
  const { user, tenant, logout } = useAuth()
  const [open, setOpen] = useState(false)

  const initials = (user?.fullName || user?.email || 'U')
    .split(' ')
    .map((s) => s[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <header className="flex h-14 items-center justify-between gap-4 border-b border-border bg-canvas px-4 sm:px-6">
      <div className="flex flex-1 items-center gap-3">
        <div className="flex items-center gap-2 lg:hidden">
          <div className="h-5 w-5 rounded-sm bg-accent" aria-hidden />
          <span className="text-sm font-semibold tracking-tight">CloudFinOps AI</span>
        </div>
        <div className="hidden md:flex items-center gap-2 rounded border border-border bg-surface px-2.5 h-9 w-full max-w-md">
          <Search size={15} className="text-ink-subtle" />
          <input
            type="text"
            placeholder="Search resources, recommendations, services"
            className="w-full bg-transparent text-sm placeholder:text-ink-subtle focus:outline-none"
          />
        </div>
      </div>
      <div className="flex items-center gap-3">
        {USE_MOCKS ? (
          <span className="hidden sm:inline-flex items-center gap-1.5 rounded-sm border border-warning-soft bg-warning-soft px-2 py-0.5 text-[11px] font-medium text-warning">
            Demo data
          </span>
        ) : null}
        <NotificationBell />
        <div className="relative">
          <button
            onClick={() => setOpen((o) => !o)}
            className="flex items-center gap-2 rounded p-0.5 hover:bg-surface-muted"
            aria-label="Account menu"
          >
            <span className="h-7 w-7 rounded-full bg-surface-muted border border-border flex items-center justify-center text-[11px] font-medium text-ink-muted">
              {initials}
            </span>
          </button>
          {open ? (
            <>
              <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} aria-hidden />
              <div className="absolute right-0 top-9 z-40 w-56 rounded border border-border bg-surface shadow-sm">
                <div className="px-3 py-2.5 border-b border-border">
                  <p className="text-xs font-medium text-ink truncate">{user?.fullName || user?.email}</p>
                  <p className="text-[11px] text-ink-subtle truncate">{user?.email}</p>
                  {tenant ? (
                    <p className="text-[11px] text-ink-subtle truncate mt-1">
                      {tenant.name} · {tenant.role}
                    </p>
                  ) : null}
                </div>
                <button
                  onClick={() => {
                    setOpen(false)
                    logout()
                  }}
                  className={clsx(
                    'w-full flex items-center gap-2 px-3 py-2 text-xs text-ink-muted hover:text-ink hover:bg-surface-muted',
                  )}
                >
                  <LogOut size={13} />
                  Sign out
                </button>
                {USE_MOCKS ? (
                  <div className="px-3 py-2 text-[10px] text-ink-subtle border-t border-border flex items-center gap-1.5">
                    <UserIcon size={10} />
                    Mock session
                  </div>
                ) : null}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </header>
  )
}