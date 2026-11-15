import { Plus, Trash2, MessageSquare } from 'lucide-react'
import { clsx } from 'clsx'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { formatDateTime } from '@/lib/format'
import { useDeleteSession, useSessions } from './sessionHooks'

export function SessionSidebar({
  activeSessionId,
  onSelect,
  onNew,
  onDeleted,
}: {
  activeSessionId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onDeleted: (id: string) => void
}) {
  const sessions = useSessions()
  const remove = useDeleteSession()

  const onDelete = (id: string, title: string) => {
    if (!window.confirm(`Delete "${title}"? This cannot be undone.`)) return
    remove.mutate(id, {
      onSuccess: () => onDeleted(id),
    })
  }

  return (
    <aside className="hidden lg:flex w-64 shrink-0 flex-col border-r border-border bg-canvas">
      <div className="flex items-center justify-between gap-2 px-3 py-3 border-b border-border">
        <span className="text-xs font-medium text-ink-muted uppercase tracking-wide">Sessions</span>
        <Button size="sm" variant="ghost" onClick={onNew} aria-label="New session">
          <Plus size={14} />
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto py-2">
        {sessions.isLoading ? (
          <div className="px-3 space-y-2">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
          </div>
        ) : sessions.isError ? (
          <StateBlock variant="error" title="Could not load sessions" />
        ) : !sessions.data || sessions.data.items.length === 0 ? (
          <StateBlock
            variant="empty"
            title="No sessions yet"
            description="Start a new conversation."
          />
        ) : (
          <ul>
            {sessions.data.items.map((s) => (
              <li key={s.id} className="px-2">
                <div
                  className={clsx(
                    'group flex items-start gap-2 rounded px-2.5 py-2 cursor-pointer transition-colors',
                    activeSessionId === s.id
                      ? 'bg-surface border border-border'
                      : 'border border-transparent hover:bg-surface-muted',
                  )}
                  onClick={() => onSelect(s.id)}
                >
                  <MessageSquare size={13} className="mt-0.5 text-ink-subtle shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-ink truncate">{s.title}</p>
                    <p className="text-[10px] text-ink-subtle mt-0.5">
                      {s.messageCount} msg · {formatDateTime(s.updatedAt)}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDelete(s.id, s.title)
                    }}
                    className="opacity-0 group-hover:opacity-100 rounded p-1 text-ink-subtle hover:text-danger"
                    aria-label="Delete session"
                  >
                    <Trash2 size={11} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  )
}