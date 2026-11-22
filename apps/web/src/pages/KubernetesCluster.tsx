import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { KpiCard } from '@/components/ui/KpiCard'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { NamespaceTable } from '@/features/kubernetes/NamespaceTable'
import { WorkloadTable } from '@/features/kubernetes/WorkloadTable'
import { useCluster } from '@/features/kubernetes/hooks'
import { formatCurrency, formatNumber } from '@/lib/format'

export function KubernetesCluster() {
  const { id } = useParams<{ id: string }>()
  const { data, isLoading, isError, refetch } = useCluster(id)

  if (isLoading) {
    return (
      <>
        <Skeleton className="h-6 w-40 mb-4" />
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 w-full" />)}
        </div>
        <Skeleton className="mt-4 h-64 w-full" />
      </>
    )
  }

  if (isError || !data) {
    return (
      <Card>
        <StateBlock
          variant="error"
          title="Cluster not found"
          action={
            <button
              onClick={() => refetch()}
              className="rounded border border-border bg-surface px-3 py-1.5 text-xs font-medium hover:border-border-strong"
            >
              Retry
            </button>
          }
        />
      </Card>
    )
  }

  const { cluster, namespaces, workloads } = data

  return (
    <>
      <div className="mb-3">
        <Link to="/kubernetes" className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink">
          <ArrowLeft size={13} /> Kubernetes
        </Link>
      </div>

      <PageHeader
        title={cluster.name}
        description={`${cluster.provider} · ${cluster.region} · Kubernetes v${cluster.version} · ${cluster.accountName}`}
        action={<Badge tone={cluster.status === 'active' ? 'success' : 'warning'}>{cluster.status}</Badge>}
      />

      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard label="Monthly cost" value={formatCurrency(cluster.monthlyCost)} hint="cluster run rate" />
        <KpiCard
          label="Nodes"
          value={formatNumber(cluster.nodeCount)}
          hint={`${cluster.totalCpuCores.toFixed(0)} vCPU · ${cluster.totalMemoryGb.toFixed(0)} GB`}
        />
        <KpiCard
          label="Workloads"
          value={formatNumber(cluster.workloadCount)}
          hint={`${cluster.namespaceCount} namespaces`}
        />
        <KpiCard
          label="Potential savings"
          value={formatCurrency(cluster.potentialSavings)}
          delta={`${cluster.overProvisionedCount} over-provisioned`}
          deltaTone="warning"
          hint="from request tuning"
        />
      </section>

      <section className="mt-4 space-y-4">
        <NamespaceTable namespaces={namespaces} />
        <WorkloadTable workloads={workloads} />
      </section>
    </>
  )
}