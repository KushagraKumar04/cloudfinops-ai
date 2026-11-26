import { ShieldAlert } from 'lucide-react'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { formatCurrency, formatDate, formatPercent } from '@/lib/format'
import { useCostAnomalies } from './hooks'
import type { CostQueryParams } from './types'

export function CostAnomalies({ query }: { query: CostQueryParams }) {
  const { data, isLoading, isError, refetch } = useCostAnomalies(query)

  return (
    <Card>
      <CardHeader
        title="Anomalies"
        subtitle="Detected by the FinOps engine"
        action={<ShieldAlert size={16} className="text-ink-subtle" />}
      />
      <CardBody className="space-y-4">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)
        ) : isError ? (
          <StateBlock
            variant="error"
            title="Could not load anomalies"
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
          <StateBlock variant="empty" title="No anomalies" description="Nothing unusual in the selected range." />
        ) : (
          data.map((a) => (
            <div key={a.id} className="border-b border-border last:border-b-0 pb-3 last:pb-0">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-ink">{a.service}</span>
                <Badge tone={a.severity === 'high' ? 'danger' : a.severity === 'medium' ? 'warning' : 'neutral'}>
                  {formatPercent(a.deltaPct, 0)}
                </Badge>
              </div>
              <p className="mt-1 text-xs text-ink-muted leading-relaxed">{a.description}</p>
              <p className="mt-1 text-[11px] text-ink-subtle">
                {a.account} · {formatDate(a.detectedAt)} · {formatCurrency(a.deltaAmount)} impact
              </p>
            </div>
          ))
        )}
      </CardBody>
    </Card>
  )
}