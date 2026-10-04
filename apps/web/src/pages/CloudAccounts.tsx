import { useState } from 'react'
import { Plus } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { CloudAccountCard } from '@/features/cloudAccounts/CloudAccountCard'
import { ConnectWizard } from '@/features/cloudAccounts/ConnectWizard'
import { useCloudAccounts, useDeleteCloudAccount } from '@/features/cloudAccounts/hooks'
import { useAuth } from '@/features/auth/useAuth'

export function CloudAccounts() {
  const { data, isLoading, isError, refetch } = useCloudAccounts()
  const [connectOpen, setConnectOpen] = useState(false)
  const remove = useDeleteCloudAccount()
  const { can } = useAuth()
  const canManage = can('manage_cloud_accounts')

  const onDelete = (id: string, name: string) => {
    if (!window.confirm(`Disconnect ${name}? This removes the connection and stops syncing. It does not delete any cloud resources.`)) return
    remove.mutate(id)
  }

  return (
    <>
      <PageHeader
        title="Cloud Accounts"
        description="Connected AWS accounts and Azure subscriptions. Connections are read-only by default."
        action={
          canManage ? (
            <Button variant="primary" size="md" onClick={() => setConnectOpen(true)}>
              <Plus size={14} /> Connect account
            </Button>
          ) : null
        }
      />

      <section className="space-y-4">
        {isLoading ? (
          Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-64 w-full" />)
        ) : isError ? (
          <div className="rounded-md border border-border bg-surface">
            <StateBlock
              variant="error"
              title="Could not load cloud accounts"
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
        ) : !data || data.length === 0 ? (
          <div className="rounded-md border border-border bg-surface">
            <StateBlock
              variant="empty"
              title="No accounts connected"
              description="Connect an AWS account or Azure subscription to begin ingesting cost and inventory data."
              action={
                canManage ? (
                  <Button variant="primary" onClick={() => setConnectOpen(true)}>
                    <Plus size={14} /> Connect account
                  </Button>
                ) : null
              }
            />
          </div>
        ) : (
          data.map((a) => (
            <CloudAccountCard
              key={a.id}
              account={a}
              onDelete={canManage ? onDelete : undefined}
            />
          ))
        )}
      </section>

      <ConnectWizard open={connectOpen} onClose={() => setConnectOpen(false)} />
    </>
  )
}