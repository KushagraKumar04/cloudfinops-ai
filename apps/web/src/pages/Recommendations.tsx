import { useSearchParams } from 'react-router-dom'
import { PageHeader } from '@/components/ui/PageHeader'
import { Pagination } from '@/components/ui/Pagination'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { RecommendationFilters } from '@/features/recommendations/RecommendationFilters'
import { RecommendationSummary } from '@/features/recommendations/RecommendationSummary'
import { RecommendationCard } from '@/features/recommendations/RecommendationCard'
import { useRecommendationList } from '@/features/recommendations/hooks'
import {
  parseRecommendationQuery,
  serializeRecommendationQuery,
} from '@/features/recommendations/queryParams'
import type { RecommendationQueryParams } from '@/features/recommendations/types'

export function Recommendations() {
  const [search, setSearch] = useSearchParams()
  const query = parseRecommendationQuery(search)
  const { data, isLoading, isError, refetch } = useRecommendationList(query)

  const update = (next: RecommendationQueryParams) => setSearch(serializeRecommendationQuery(next), { replace: true })

  return (
    <>
      <PageHeader
        title="Recommendations"
        description="Evidence-backed optimization candidates produced by the FinOps engine."
      />

      <RecommendationFilters value={query} onChange={update} />

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
          <RecommendationSummary totals={data.totals} />
        )}
      </section>

      <section className="mt-4 space-y-3">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-32 w-full" />)
        ) : isError ? (
          <div className="rounded-md border border-border bg-surface">
            <StateBlock
              variant="error"
              title="Could not load recommendations"
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
        ) : !data || data.items.length === 0 ? (
          <div className="rounded-md border border-border bg-surface">
            <StateBlock
              variant="empty"
              title="No recommendations match"
              description="Adjust filters or clear the search to see candidates."
            />
          </div>
        ) : (
          <>
            {data.items.map((r) => (
              <RecommendationCard key={r.id} rec={r} />
            ))}
            <div className="rounded-md border border-border bg-surface">
              <Pagination
                page={query.page}
                pageSize={query.pageSize}
                total={data.total}
                onPageChange={(page) => update({ ...query, page })}
              />
            </div>
          </>
        )}
      </section>
    </>
  )
}