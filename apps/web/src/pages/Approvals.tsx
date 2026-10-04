import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { formatCurrency, formatDateTime } from '@/lib/format'
import { RiskBadge } from '@/features/recommendations/badges'
import { useRecommendationDecision, useRecommendationList } from '@/features/recommendations/hooks'
import { useAuth } from '@/features/auth/useAuth'
import { parseRecommendationQuery } from '@/features/recommendations/queryParams'
import type { Recommendation } from '@/features/recommendations/types'

export function Approvals() {
  const baseQuery = parseRecommendationQuery(new URLSearchParams())
  const query = {
    ...baseQuery,
    status: 'pending' as const,
    sortKey: 'estimatedMonthlySavings' as const,
    sortDir: 'desc' as const,
    pageSize: 20,
  }
  const { data, isLoading, isError, refetch } = useRecommendationList(query)
  const { can } = useAuth()
  const canApprove = can('approve_recommendation')

  const [approving, setApproving] = useState<Recommendation | null>(null)
  const [rejecting, setRejecting] = useState<Recommendation | null>(null)
  const [reason, setReason] = useState('')

  const approveMut = useRecommendationDecision(approving?.id ?? '')
  const rejectMut = useRecommendationDecision(rejecting?.id ?? '')

  const items = (data?.items ?? []).filter((r) => r.risk !== 'BLOCKED')
  const blocked = (data?.items ?? []).filter((r) => r.risk === 'BLOCKED')

  const onApprove = () => {
    if (!approving) return
    approveMut.mutate(
      { action: 'approve' },
      {
        onSuccess: () => {
          setApproving(null)
          refetch()
        },
      },
    )
  }

  const onReject = () => {
    if (!rejecting || !reason.trim()) return
    rejectMut.mutate(
      { action: 'reject', reason: reason.trim() },
      {
        onSuccess: () => {
          setRejecting(null)
          setReason('')
          refetch()
        },
      },
    )
  }

  return (
    <>
      <PageHeader
        title="Approvals"
        description="Pending recommendations awaiting a decision. Approving here does not execute the change; execution is a separate policy-gated step."
      />

      <Card className="px-5 py-4">
        <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
          <div>
            <p className="text-[11px] font-medium text-ink-muted uppercase tracking-wide">Awaiting decision</p>
            <p className="mt-1 text-lg font-semibold tabular-nums">{isLoading ? '—' : items.length}</p>
          </div>
          <div>
            <p className="text-[11px] font-medium text-ink-muted uppercase tracking-wide">Pending savings</p>
            <p className="mt-1 text-lg font-semibold tabular-nums text-success">
              {formatCurrency(items.reduce((s, r) => s + r.estimatedMonthlySavings, 0))}
              <span className="text-xs text-ink-muted font-normal"> /mo</span>
            </p>
          </div>
          <div>
            <p className="text-[11px] font-medium text-ink-muted uppercase tracking-wide">Blocked by policy</p>
            <p className="mt-1 text-lg font-semibold tabular-nums text-ink-muted">{isLoading ? '—' : blocked.length}</p>
          </div>
        </div>
      </Card>

      <section className="mt-4 space-y-3">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 w-full" />)
        ) : isError ? (
          <div className="rounded-md border border-border bg-surface">
            <StateBlock
              variant="error"
              title="Could not load approvals"
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
        ) : items.length === 0 ? (
          <div className="rounded-md border border-border bg-surface">
            <StateBlock
              variant="empty"
              title="Nothing to approve"
              description="All pending recommendations have been decided."
            />
          </div>
        ) : (
          items.map((r) => (
            <Card key={r.id}>
              <CardHeader
                title={r.title}
                subtitle={`${r.typeLabel} · ${r.resourceName} · ${r.accountName}`}
                action={<RiskBadge risk={r.risk} />}
              />
              <CardBody className="pt-0">
                <p className="text-sm text-ink-muted leading-relaxed line-clamp-2">{r.summary}</p>
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-4 text-xs">
                    <span className="text-ink-muted">
                      Savings <span className="text-success font-medium tabular-nums">{formatCurrency(r.estimatedMonthlySavings)}/mo</span>
                    </span>
                    <span className="text-ink-muted">
                      Confidence <span className="text-ink font-medium">{Math.round(r.confidence * 100)}%</span>
                    </span>
                    <span className="text-ink-subtle">Created {formatDateTime(r.createdAt)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/recommendations/${r.id}`}
                      className="inline-flex items-center gap-1 text-xs font-medium text-ink-muted hover:text-ink px-2 py-1"
                    >
                      Review <ArrowRight size={12} />
                    </Link>
                    {canApprove ? (
                      <>
                        <Button size="sm" variant="secondary" onClick={() => { setRejecting(r); setReason('') }}>
                          Reject
                        </Button>
                        <Button size="sm" variant="primary" onClick={() => setApproving(r)}>
                          Approve
                        </Button>
                      </>
                    ) : null}
                  </div>
                </div>
              </CardBody>
            </Card>
          ))
        )}
      </section>

      {blocked.length > 0 ? (
        <section className="mt-6">
          <h2 className="text-sm font-semibold text-ink mb-3">Blocked by policy</h2>
          <div className="space-y-3">
            {blocked.map((r) => (
              <Card key={r.id} className="opacity-90">
                <CardHeader
                  title={r.title}
                  subtitle={`${r.typeLabel} · ${r.resourceName}`}
                  action={<RiskBadge risk={r.risk} />}
                />
                <CardBody className="pt-0">
                  <ul className="text-xs text-ink-muted list-disc list-inside space-y-0.5">
                    {r.riskReasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                  <Link
                    to={`/recommendations/${r.id}`}
                    className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
                  >
                    View details <ArrowRight size={12} />
                  </Link>
                </CardBody>
              </Card>
            ))}
          </div>
        </section>
      ) : null}

      <Modal
        open={approving !== null}
        onClose={() => setApproving(null)}
        title="Approve recommendation"
        description="Approving creates an execution plan. No cloud resource will be modified until a policy check, dry run, and re-validation have passed."
        footer={
          <>
            <Button variant="ghost" onClick={() => setApproving(null)} disabled={approveMut.isPending}>
              Cancel
            </Button>
            <Button variant="primary" onClick={onApprove} disabled={approveMut.isPending}>
              {approveMut.isPending ? 'Submitting…' : 'Confirm approval'}
            </Button>
          </>
        }
      >
        {approving ? (
          <div className="space-y-3 text-sm">
            <p className="text-ink">{approving.title}</p>
            <div className="flex items-center gap-3 text-xs text-ink-muted">
              <span>Savings <span className="text-success font-medium tabular-nums">{formatCurrency(approving.estimatedMonthlySavings)}/mo</span></span>
              <span>Risk <span className="text-ink font-medium">{approving.risk}</span></span>
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal
        open={rejecting !== null}
        onClose={() => { setRejecting(null); setReason('') }}
        title="Reject recommendation"
        description="Provide a reason. The reason is stored on the recommendation and recorded in the audit log."
        footer={
          <>
            <Button variant="ghost" onClick={() => { setRejecting(null); setReason('') }} disabled={rejectMut.isPending}>
              Cancel
            </Button>
            <Button variant="danger" onClick={onReject} disabled={rejectMut.isPending || !reason.trim()}>
              {rejectMut.isPending ? 'Submitting…' : 'Confirm rejection'}
            </Button>
          </>
        }
      >
        <label className="block">
          <span className="text-xs font-medium text-ink">Reason (required)</span>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            className="mt-1.5 w-full rounded border border-border bg-surface px-3 py-2 text-sm focus:border-accent focus:outline-none"
            placeholder="Why is this recommendation being rejected?"
          />
        </label>
      </Modal>
    </>
  )
}