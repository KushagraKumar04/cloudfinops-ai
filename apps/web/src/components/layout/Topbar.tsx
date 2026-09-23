import { Search, Bell } from 'lucide-react'

export function Topbar() {
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
        <span className="hidden sm:inline-flex items-center gap-1.5 rounded-sm border border-warning-soft bg-warning-soft px-2 py-0.5 text-[11px] font-medium text-warning">
          Demo data
        </span>
        <button className="rounded p-1.5 text-ink-muted hover:text-ink hover:bg-surface-muted" aria-label="Notifications">
          <Bell size={16} />
        </button>
        <div className="h-7 w-7 rounded-full bg-surface-muted border border-border flex items-center justify-center text-[11px] font-medium text-ink-muted">
          JD
        </div>
      </div>
    </header>
  )
}