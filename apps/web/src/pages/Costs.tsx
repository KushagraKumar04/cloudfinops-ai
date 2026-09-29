import { useSearchParams } from 'react-router-dom'
import { PageHeader } from '@/components/ui/PageHeader'
import { KpiCard } from '@/components/ui/KpiCard'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { formatCurrency, formatPercent } from '@/lib/format'
import { CostFilters } from '@/features/costs/CostFilters'
import { CostTrendChart } from '@/features/costs/CostTrendChart'
import { CostBreakdownTable } from '@/features/costs/CostBreakdownTable'
import { CostAnomalies } from '@/features/costs/CostAnomalies'
import { useCostSummary, useCostTrend } from '@/features/costs/hooks'
import { parseCostQuery, rangeLabel, serializeCostQuery } from '@/features/costs/queryParams'
import type { CostQueryParams } from '@/features/costs/types'

export function Costs() {
  const [search, setSearch] = useSearchParams()
  const query = parseCostQuery(search)
  const summary = useCostSummary(query)
  const trend = useCostTrend(query)

  const updateQuery = (next: CostQueryParams) => setSearch(serializeCostQuery(next), { replace: true })

  return (
    <>
      <PageHeader
        title="Costs"
        description="Analyze spend by provider, service, account, and region."
        action={<span className="text-xs text-ink-muted">{rangeLabel(query.range)}</span>}
      />

      <CostFilters value={query} onChange={updateQuery} />

      <section className="mt-4 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {summary.isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 w-full" />)
        ) : summary.isError || !summary.data ? (
          <div className="col-span-full">
            <div className="rounded-md border border-border bg-surface">
              <StateBlock
                variant="error"
                title="Could not load cost summary"
                description="The summary endpoint did not respond."
                action={
                  <button
                    onClick={() => summary.refetch()}
                    className="rounded border border-border bg-surface px-3 py-1.5 text-xs font-medium hover:border-border-strong"
                  >
                    Retry
                  </button>
                }
              />
            </div>
          </div>
        ) : (
          <>
            <KpiCard
              label="Spend in range"
              value={formatCurrency(summary.data.currentSpend)}
              delta={formatPercent(summary.data.changePct)}
              deltaTone={summary.data.changePct > 0 ? 'danger' : 'success'}
              hint="vs previous period"
            />
            <KpiCard
              label="Previous period"
              value={formatCurrency(summary.data.previousSpend)}
              hint={`${summary.data.period.start} → ${summary.data.period.end}`}
            />
            <KpiCard
              label="Change"
              value={formatCurrency(summary.data.changeAmount)}
              deltaTone={summary.data.changeAmount > 0 ? 'danger' : 'success'}
              hint="absolute difference"
            />
            <KpiCard
              label="Top mover"
              value={summary.data.topMover?.name ?? '—'}
              delta={summary.data.topMover ? formatPercent(summary.data.topMover.deltaPct) : undefined}
              deltaTone="danger"
              hint={summary.data.topMover ? formatCurrency(summary.data.topMover.deltaAmount) : undefined}
            />
          </>
        )}
      </section>

      <section className="mt-4">
        <CostTrendChart
          data={trend.data}
          isLoading={trend.isLoading}
          isError={trend.isError}
          onRetry={() => trend.refetch()}
          query={query}
        />
      </section>

      <section className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <CostBreakdownTable query={query} />
        </div>
        <CostAnomalies query={query} />
      </section>
    </>
  )
}