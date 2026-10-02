import { useSearchParams } from 'react-router-dom'
import { PageHeader } from '@/components/ui/PageHeader'
import { Pagination } from '@/components/ui/Pagination'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { ResourceFilters } from '@/features/resources/ResourceFilters'
import { ResourceTable } from '@/features/resources/ResourceTable'
import { ResourceSummary } from '@/features/resources/ResourceSummary'
import { useResourceList } from '@/features/resources/hooks'
import { parseResourceQuery, serializeResourceQuery } from '@/features/resources/queryParams'
import type { ResourceQueryParams, SortKey } from '@/features/resources/types'

export function Resources() {
  const [search, setSearch] = useSearchParams()
  const query = parseResourceQuery(search)
  const { data, isLoading, isError, refetch } = useResourceList(query)

  const update = (next: ResourceQueryParams) => setSearch(serializeResourceQuery(next), { replace: true })

  const onSort = (key: SortKey) => {
    const dir: ResourceQueryParams['sortDir'] = query.sortKey === key && query.sortDir === 'desc' ? 'asc' : 'desc'
    update({ ...query, sortKey: key, sortDir: dir, page: 1 })
  }

  return (
    <>
      <PageHeader
        title="Resources"
        description="Inventory across AWS and Azure with utilization and cost signals."
      />

      <ResourceFilters value={query} onChange={update} />

      <section className="mt-4">
        {isLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : isError || !data ? (
          <div className="rounded-md border border-border bg-surface">
            <StateBlock
              variant="error"
              title="Could not load summary"
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
          <ResourceSummary aggregates={data.aggregates} />
        )}
      </section>

      <section className="mt-4">
        <ResourceTable
          data={data?.items}
          isLoading={isLoading}
          isError={isError}
          onRetry={() => refetch()}
          query={query}
          onSort={onSort}
        />
        {data && data.total > 0 ? (
          <div className="mt-0 rounded-b-md border border-t-0 border-border bg-surface">
            <Pagination
              page={query.page}
              pageSize={query.pageSize}
              total={data.total}
              onPageChange={(page) => update({ ...query, page })}
            />
          </div>
        ) : null}
      </section>
    </>
  )
}