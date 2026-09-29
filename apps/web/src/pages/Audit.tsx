import { useSearchParams } from 'react-router-dom'
import { PageHeader } from '@/components/ui/PageHeader'
import { Card, CardBody } from '@/components/ui/Card'
import { Pagination } from '@/components/ui/Pagination'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { AuditFilters } from '@/features/audit/AuditFilters'
import { AuditTimeline } from '@/features/audit/AuditTimeline'
import { useAuditList } from '@/features/audit/hooks'
import { parseAuditQuery, serializeAuditQuery } from '@/features/audit/queryParams'
import type { AuditQueryParams } from '@/features/audit/types'

export function Audit() {
  const [search, setSearch] = useSearchParams()
  const query = parseAuditQuery(search)
  const { data, isLoading, isError, refetch } = useAuditList(query)

  const update = (next: AuditQueryParams) => setSearch(serializeAuditQuery(next), { replace: true })

  return (
    <>
      <PageHeader
        title="Audit"
        description="Immutable log of privileged operations, decisions, syncs, and policy actions."
      />

      <AuditFilters value={query} onChange={update} />

      <section className="mt-4">
        <Card>
          <CardBody className="pt-5">
            {isLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-24 w-full" />
                ))}
              </div>
            ) : isError ? (
              <StateBlock
                variant="error"
                title="Could not load audit log"
                action={
                  <button
                    onClick={() => refetch()}
                    className="rounded border border-border bg-surface px-3 py-1.5 text-xs font-medium hover:border-border-strong"
                  >
                    Retry
                  </button>
                }
              />
            ) : !data || data.items.length === 0 ? (
              <StateBlock
                variant="empty"
                title="No events match"
                description="Adjust the filters or clear the search."
              />
            ) : (
              <AuditTimeline events={data.items} />
            )}
          </CardBody>
          {data && data.total > 0 ? (
            <Pagination
              page={query.page}
              pageSize={query.pageSize}
              total={data.total}
              onPageChange={(page) => update({ ...query, page })}
            />
          ) : null}
        </Card>
      </section>
    </>
  )
}