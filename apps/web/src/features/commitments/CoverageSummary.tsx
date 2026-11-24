import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { formatCurrency } from '@/lib/format'
import type { CoverageSummary as CoverageSummaryType } from './types'

export function CoverageSummaryCard({ summary }: { summary: CoverageSummaryType }) {
  const coveragePct = Math.round(summary.coveragePct * 1000) / 10
  const utilizationPct = Math.round(summary.averageUtilizationPct * 1000) / 10
  const coverageTone =
    coveragePct >= 70 ? 'success' : coveragePct >= 40 ? 'warning' : 'danger'

  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-medium text-ink-muted uppercase tracking-wide">Commitment coverage</p>
          <div className="mt-1 flex items-baseline gap-3">
            <p className="text-3xl font-semibold text-ink tabular-nums">{coveragePct.toFixed(1)}%</p>
            <Badge tone={coverageTone}>
              {coveragePct >= 70 ? 'Healthy' : coveragePct >= 40 ? 'Partial' : 'Low'}
            </Badge>
          </div>
          <p className="mt-1 text-xs text-ink-muted">
            {formatCurrency(summary.coveredMonthlySpend)} of {formatCurrency(summary.eligibleMonthlySpend)} eligible spend is covered
          </p>
        </div>
        <div className="text-right">
          <p className="text-[11px] font-medium text-ink-muted uppercase tracking-wide">Realized savings</p>
          <p className="mt-1 text-lg font-semibold text-success tabular-nums">
            {formatCurrency(summary.realizedMonthlySavings)}
            <span className="text-xs font-normal text-ink-muted"> /mo</span>
          </p>
          <p className="mt-0.5 text-xs text-ink-muted">
            {formatCurrency(summary.potentialMonthlySavings)} available
          </p>
        </div>
      </div>

      <div>
        <div className="h-2 w-full rounded-full bg-surface-muted overflow-hidden">
          <div
            className={`h-full rounded-full ${
              coveragePct >= 70 ? 'bg-success' : coveragePct >= 40 ? 'bg-warning' : 'bg-danger'
            }`}
            style={{ width: `${Math.max(2, Math.min(100, coveragePct))}%` }}
          />
        </div>
        <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <Stat label="Active commitments" value={String(summary.activeCommitments)} />
          <Stat label="Avg utilization" value={`${utilizationPct.toFixed(1)}%`} />
          <Stat label="Expiring ≤60d" value={String(summary.expiringWithin60Days)} warn={summary.expiringWithin60Days > 0} />
          <Stat label="On-demand risk" value={`${(summary.onDemandRiskPct * 100).toFixed(1)}%`} />
        </div>
      </div>
    </Card>
  )
}

function Stat({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">{label}</p>
      <p className={`mt-0.5 tabular-nums ${warn ? 'text-warning font-medium' : 'text-ink'}`}>{value}</p>
    </div>
  )
}