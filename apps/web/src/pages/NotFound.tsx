import { PageHeader } from '@/components/ui/PageHeader'

export function NotFound() {
  return (
    <>
      <PageHeader title="Not found" description="Analyze spend by provider, service, account, and time." />
      <div className="rounded-md border border-border bg-surface p-10 text-center text-sm text-ink-muted">
        The page you are looking for does not exist.
      </div>
    </>
  )
}