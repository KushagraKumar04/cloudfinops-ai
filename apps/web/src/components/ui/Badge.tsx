import { clsx } from 'clsx'
import type { ReactNode } from 'react'

type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger'

const toneClass: Record<Tone, string> = {
  neutral: 'bg-surface-muted text-ink-muted border-border',
  accent: 'bg-accent-soft text-accent border-accent-soft',
  success: 'bg-success-soft text-success border-success-soft',
  warning: 'bg-warning-soft text-warning border-warning-soft',
  danger: 'bg-danger-soft text-danger border-danger-soft',
}

export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-[11px] font-medium leading-none',
        toneClass[tone],
      )}
    >
      {children}
    </span>
  )
}