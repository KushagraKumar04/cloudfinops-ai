import { clsx } from 'clsx'
import type { ReactNode } from 'react'
import { Card } from './Card'

export function KpiCard({
  label,
  value,
  delta,
  deltaTone = 'neutral',
  hint,
}: {
  label: string
  value: ReactNode
  delta?: string
  deltaTone?: 'neutral' | 'success' | 'warning' | 'danger'
  hint?: string
}) {
  const toneClass = {
    neutral: 'text-ink-muted',
    success: 'text-success',
    warning: 'text-warning',
    danger: 'text-danger',
  }[deltaTone]

  return (
    <Card className="p-5">
      <p className="text-xs font-medium text-ink-muted uppercase tracking-wide">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-ink tabular-nums">{value}</p>
      <div className="mt-2 flex items-center gap-2 text-xs">
        {delta ? <span className={clsx('font-medium tabular-nums', toneClass)}>{delta}</span> : null}
        {hint ? <span className="text-ink-subtle">{hint}</span> : null}
      </div>
    </Card>
  )
}