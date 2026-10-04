import { useSearchParams } from 'react-router-dom'
import { ArrowDown, ArrowUp, Minus } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { KpiCard } from '@/components/ui/KpiCard'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { formatCurrency, formatPercent } from '@/lib/format'
import { ForecastFilters } from '@/features/forecast/ForecastFilters'
import { ForecastChart } from '@/features/forecast/ForecastChart'
import { ServiceForecastTable } from '@/features/forecast/ServiceForecastTable'
import { ScenarioList } from '@/features/forecast/ScenarioList'
import {
  useForecastSeries,
  useForecastSummary,
  useScenarios,
  useServiceForecast,
} from '@/features/forecast/hooks'
import { parseForecastQuery, serializeForecastQuery } from '@/features/forecast/queryParams'
import type { ForecastQueryParams } from '@/features/forecast/types'

export function Forecast() {
  const [search, setSearch] = useSearchParams()
  const query = parseForecastQuery(search)
  const summary = useForecastSummary(query)
  const series = useForecastSeries(query)
  const services = useServiceForecast(query)
  const scenarios = useScenarios(query)

  const update = (next: ForecastQueryParams) => setSearch(serializeForecastQuery(next), { replace: true })

  const trendIcon =
    summary.data?.trendDirection === 'up' ? (
      <ArrowUp size={12} />
    ) : summary.data?.trendDirection === 'down' ? (
      <ArrowDown size={12} />
    ) : (
      <Minus size={12} />
    )

  const budgetTone =
    summary.data && summary.data.budgetUtilization >= 100
      ? 'danger'
      : summary.data && summary.data.budgetUtilization >= 95
        ? 'warning'
        : 'success'

  return (
    <>
      <PageHeader
        title="Forecast"
        description="Projected spend with confidence intervals, per-service breakdown, and what-if scenarios."
      />

      <ForecastFilters value={query} onChange={update} />

      <section className="mt-4 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {summary.isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 w-full" />)
        ) : summary.isError || !summary.data ? (
          <div className="col-span-full rounded-md border border-border bg-surface">
            <StateBlock
              variant="error"
              title="Could not load forecast summary"
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
        ) : (
          <>
            <KpiCard
              label="Projected month-end"
              value={formatCurrency(summary.data.monthEndProjection)}
              delta={`${formatCurrency(summary.data.monthEndLower)} – ${formatCurrency(summary.data.monthEndUpper)}`}
              deltaTone="neutral"
              hint="80% confidence interval"
            />
            <KpiCard
              label="Budget utilization"
              value={`${summary.data.budgetUtilization.toFixed(1)}%`}
              delta={`${formatCurrency(summary.data.budget)} budget`}
              deltaTone={budgetTone}
              hint={`Breach risk ${Math.round(summary.data.breachProbability * 100)}%`}
            />
            <KpiCard
              label="Trend"
              value={
                <span className="inline-flex items-center gap-1.5">
                  {trendIcon}
                  {formatPercent(summary.data.trendPct)}
                </span>
              }
              hint={`over ${summary.data.horizon} horizon`}
            />
            <KpiCard
              label="Model confidence"
              value={`${Math.round(summary.data.confidence * 100)}%`}
              hint="deterministic + seasonal"
            />
          </>
        )}
      </section>

      <section className="mt-4">
        <ForecastChart
          data={series.data}
          budget={query.budget}
          isLoading={series.isLoading}
          isError={series.isError}
          onRetry={() => series.refetch()}
        />
      </section>

      <section className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <ServiceForecastTable
            data={services.data}
            isLoading={services.isLoading}
            isError={services.isError}
            onRetry={() => services.refetch()}
          />
        </div>
        <ScenarioList
          data={scenarios.data}
          budget={query.budget}
          isLoading={scenarios.isLoading}
          isError={scenarios.isError}
          onRetry={() => scenarios.refetch()}
        />
      </section>
    </>
  )
}