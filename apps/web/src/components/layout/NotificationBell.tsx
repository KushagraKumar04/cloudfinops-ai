import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bell, CheckCheck, Loader2 } from 'lucide-react'
import { clsx } from 'clsx'
import { formatDateTime } from '@/lib/format'
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useRecentNotifications,
} from '@/features/notifications/hooks'
import type { NotificationDelivery, Severity } from '@/features/notifications/types'

const SEVERITY_DOT: Record<Severity, string> = {
  info: 'bg-accent',
  warning: 'bg-warning',
  critical: 'bg-danger',
}

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const notifications = useRecentNotifications(5)
  const markRead = useMarkNotificationRead()
  const markAll = useMarkAllNotificationsRead()

  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const unread = notifications.data?.unread ?? 0
  const items = notifications.data?.items ?? []

  const onOpenItem = (item: NotificationDelivery) => {
    if (!item.readAt) markRead.mutate(item.id)
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className={clsx(
          'relative rounded p-1.5 transition-colors',
          open ? 'bg-surface-muted text-ink' : 'text-ink-muted hover:text-ink hover:bg-surface-muted',
        )}
        aria-label={unread > 0 ? `Notifications, ${unread} unread` : 'Notifications'}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <Bell size={16} />
        {unread > 0 ? (
          <span className="absolute -top-0.5 -right-0.5 inline-flex items-center justify-center min-w-[14px] h-[14px] rounded-full bg-danger text-white text-[9px] font-semibold px-1 tabular-nums">
            {unread > 99 ? '99+' : unread}
          </span>
        ) : null}
      </button>

      {open ? (
        <div
          role="menu"
          className="absolute right-0 top-9 z-40 w-[360px] rounded border border-border bg-surface shadow-sm overflow-hidden"
        >
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-border">
            <span className="text-xs font-medium text-ink-muted uppercase tracking-wide">
              Notifications
            </span>
            {unread > 0 ? (
              <button
                onClick={() => markAll.mutate()}
                disabled={markAll.isPending}
                className="inline-flex items-center gap-1 text-[11px] text-accent hover:underline disabled:opacity-60"
              >
                {markAll.isPending ? (
                  <Loader2 size={11} className="animate-spin" />
                ) : (
                  <CheckCheck size={11} />
                )}
                Mark all read
              </button>
            ) : null}
          </div>

          <div className="max-h-[360px] overflow-y-auto">
            {notifications.isLoading ? (
              <div className="px-3 py-6 text-center text-xs text-ink-muted">
                <Loader2 size={13} className="inline animate-spin mr-1" /> Loading…
              </div>
            ) : items.length === 0 ? (
              <div className="px-3 py-8 text-center text-xs text-ink-muted">
                No notifications yet.
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {items.map((item) => (
                  <li key={item.id}>
                    <button
                      onClick={() => onOpenItem(item)}
                      className={clsx(
                        'w-full text-left px-3 py-2.5 transition-colors',
                        item.readAt ? 'hover:bg-surface-muted/50' : 'bg-accent-soft/40 hover:bg-accent-soft/60',
                      )}
                    >
                      <div className="flex items-start gap-2">
                        <span
                          className={clsx(
                            'mt-1.5 h-1.5 w-1.5 rounded-full shrink-0',
                            SEVERITY_DOT[item.severity],
                          )}
                        />
                        <div className="min-w-0 flex-1">
                          <p
                            className={clsx(
                              'text-xs leading-snug truncate',
                              item.readAt ? 'text-ink-muted' : 'text-ink font-medium',
                            )}
                          >
                            {item.subject}
                          </p>
                          <div className="mt-0.5 flex items-center gap-2 text-[10px] text-ink-subtle">
                            <span>{item.eventType}</span>
                            <span aria-hidden>·</span>
                            <span>{formatDateTime(item.createdAt)}</span>
                          </div>
                        </div>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <Link
            to="/notifications"
            onClick={() => setOpen(false)}
            className="block border-t border-border px-3 py-2 text-center text-[11px] font-medium text-accent hover:bg-surface-muted/50"
          >
            View all notifications
          </Link>
        </div>
      ) : null}
    </div>
  )
}