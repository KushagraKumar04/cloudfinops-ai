import { PageHeader } from '@/components/ui/PageHeader'

export function Forecast() {
  return (
    <>
      <PageHeader title="Forecast" description="Analyze spend by provider, service, account, and time." />
      <div className="rounded-md border border-border bg-surface p-10 text-center text-sm text-ink-muted">
        Forecast view coming in the next batch.
      </div>
    </>
  )
}