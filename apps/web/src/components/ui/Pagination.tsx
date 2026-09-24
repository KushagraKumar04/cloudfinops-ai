import { ChevronLeft, ChevronRight } from 'lucide-react'
import { clsx } from 'clsx'

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
}

export function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1
  const end = Math.min(total, page * pageSize)
  const prevDisabled = page <= 1
  const nextDisabled = page >= pageCount

  const btn = 'inline-flex h-7 w-7 items-center justify-center rounded border border-border bg-surface text-ink-muted hover:text-ink hover:border-border-strong disabled:opacity-40 disabled:cursor-not-allowed'

  return (
    <div className="flex items-center justify-between gap-3 px-5 py-3 border-t border-border">
      <p className="text-xs text-ink-muted tabular-nums">
        {start}–{end} of {total}
      </p>
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          className={clsx(btn)}
          onClick={() => onPageChange(page - 1)}
          disabled={prevDisabled}
          aria-label="Previous page"
        >
          <ChevronLeft size={14} />
        </button>
        <span className="text-xs text-ink-muted tabular-nums px-1">
          {page} / {pageCount}
        </span>
        <button
          type="button"
          className={clsx(btn)}
          onClick={() => onPageChange(page + 1)}
          disabled={nextDisabled}
          aria-label="Next page"
        >
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  )
}