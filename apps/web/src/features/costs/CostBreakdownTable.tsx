import { useState } from 'react'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { Tabs } from '@/components/ui/Tabs'
import { clsx } from 'clsx'
import { formatCurrency, formatPercent } from '@/lib/format'
import { useCostBreakdown } from './hooks'
import type { BreakdownDimension, CostQueryParams } from './types'

const DIMS: { value: BreakdownDimension; label: string }[] = [
  { value: 'service', label: 'Service' },
  { value: 'account', label: 'Account' },
  { value: 'region', label: 'Region' },
]

export function CostBreakdownTable({ query }: { query: CostQueryParams }) {
  const [dim, setDim] = useState<BreakdownDimension>('service')
  const { data, isLoading, isError, refetch } = useCostBreakdown(query, dim)

  return (
    <Card>
      <CardHeader
        title="Breakdown"
        subtitle="Share of spend and change vs previous period"
        action={<Tabs<BreakdownDimension> ariaLabel="Breakdown dimension" value={dim} onChange={setDim} items={DIMS} />}
      />
      <CardBody className="p-0">
        {isLoading ? (
          <div className="space-y-2 px-5 pb-5">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : isError ? (
          <StateBlock
            variant="error"
            title="Could not load breakdown"
            action={
              <button
                onClick={() => refetch()}
                className="rounded border border-border bg-surface px-3 py-1.5 text-xs font-medium hover:border-border-strong"
              >
                Retry
              </button>
            }
          />
        ) : !data || data.length === 0 ? (
          <StateBlock variant="empty" title="No breakdown available" description="Try widening the filters." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-ink-muted">
                <th className="px-5 py-2 font-medium">Name</th>
                <th className="px-5 py-2 font-medium">Provider</th>
                <th className="px-5 py-2 font-medium text-right">Spend</th>
                <th className="px-5 py-2 font-medium">Share</th>
                <th className="px-5 py-2 font-medium text-right">Change</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.id} className="border-b border-border last:border-b-0">
                  <td className="px-5 py-3 text-ink">{row.name}</td>
                  <td className="px-5 py-3 text-ink-muted">{row.provider === 'mixed' ? 'Mixed' : row.provider}</td>
                  <td className="px-5 py-3 text-right tabular-nums">{formatCurrency(row.spend)}</td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-24 rounded-full bg-surface-muted">
                        <div className="h-full rounded-full bg-accent" style={{ width: `${Math.max(2, Math.round(row.share * 100))}%` }} />
                      </div>
                      <span className="text-xs text-ink-muted tabular-nums">{Math.round(row.share * 100)}%</span>
                    </div>
                  </td>
                  <td
                    className={clsx(
                      'px-5 py-3 text-right tabular-nums',
                      row.changePct > 0 ? 'text-danger' : row.changePct < 0 ? 'text-success' : 'text-ink-muted',
                    )}
                  >
                    {formatPercent(row.changePct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardBody>
    </Card>
  )
}