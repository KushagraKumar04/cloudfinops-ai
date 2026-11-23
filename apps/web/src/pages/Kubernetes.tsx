import { PageHeader } from '@/components/ui/PageHeader'
import { KpiCard } from '@/components/ui/KpiCard'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { ClusterCard } from '@/features/kubernetes/ClusterCard'
import { useClusters } from '@/features/kubernetes/hooks'
import { formatCurrency, formatNumber } from '@/lib/format'

export function Kubernetes() {
  const { data, isLoading, isError, refetch } = useClusters()

  return (
    <>
      <PageHeader
        title="Kubernetes"
        description="Cluster cost allocation, namespace breakdown, and workload rightsizing candidates."
      />

      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 w-full" />)
        ) : isError || !data ? (
          <div className="col-span-full rounded-md border border-border bg-surface">
            <StateBlock
              variant="error"
              title="Could not load clusters"
              action={
                <button
                  onClick={() => refetch()}
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
              label="Clusters"
              value={formatNumber(data.aggregates.cluster_count)}
              hint="across all connected accounts"
            />
            <KpiCard
              label="Nodes"
              value={formatNumber(data.aggregates.node_count)}
              hint={`${data.aggregates.total_cpu_cores.toFixed(0)} vCPU · ${data.aggregates.total_memory_gb.toFixed(0)} GB`}
            />
            <KpiCard
              label="Monthly cost"
              value={formatCurrency(data.aggregates.total_monthly_cost)}
              hint="compute + memory + storage"
            />
            <KpiCard
              label="Potential savings"
              value={formatCurrency(data.items.reduce((s, c) => s + c.potentialSavings, 0))}
              delta={`${data.items.reduce((s, c) => s + c.overProvisionedCount, 0)} over-provisioned`}
              deltaTone="warning"
              hint="from rightsizing requests"
            />
          </>
        )}
      </section>

      <section className="mt-4 space-y-3">
        {isLoading ? (
          Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-40 w-full" />)
        ) : isError ? null : !data || data.items.length === 0 ? (
          <div className="rounded-md border border-border bg-surface">
            <StateBlock
              variant="empty"
              title="No Kubernetes clusters connected"
              description="Connect an AWS or Azure account with EKS or AKS to see cost allocation."
            />
          </div>
        ) : (
          data.items.map((c) => <ClusterCard key={c.id} cluster={c} />)
        )}
      </section>
    </>
  )
}