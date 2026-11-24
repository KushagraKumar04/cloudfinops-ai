import { useState } from 'react'
import { ArrowRight, Loader2 } from 'lucide-react'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { clsx } from 'clsx'
import { formatCurrency, formatPercent } from '@/lib/format'
import { useDecideCommitmentRecommendation } from './hooks'
import type { CommitmentRecommendation, RiskLevel } from './types'

const RISK_TONE: Record<RiskLevel, 'success' | 'warning' | 'danger' | 'neutral'> = {
  LOW: 'success',
  MEDIUM: 'warning',
  HIGH: 'danger',
  BLOCKED: 'neutral',
}

export function RecommendationList({
  items,
  canManage,
}: {
  items: CommitmentRecommendation[]
  canManage: boolean
}) {
  const [approving, setApproving] = useState<CommitmentRecommendation | null>(null)
  const [rejecting, setRejecting] = useState<CommitmentRecommendation | null>(null)
  const [reason, setReason] = useState('')
  const decide = useDecideCommitmentRecommendation()

  const confirmApprove = () => {
    if (!approving) return
    decide.mutate(
      { id: approving.id, decision: 'approve' },
      { onSuccess: () => setApproving(null) },
    )
  }

  const confirmReject = () => {
    if (!rejecting || !reason.trim()) return
    decide.mutate(
      { id: rejecting.id, decision: 'reject', reason: reason.trim() },
      {
        onSuccess: () => {
          setRejecting(null)
          setReason('')
        },
      },
    )
  }

  return (
    <>
      <Card>
        <CardHeader
          title="Recommendations"
          subtitle="Deterministic purchase analyses based on 30-day usage and public pricing"
        />
        <CardBody className="p-0">
          {items.length === 0 ? (
            <div className="px-5 py-10 text-center text-sm text-ink-muted">No pending recommendations.</div>
          ) : (
            <div className="divide-y divide-border">
              {items.map((r) => {
                const deltaPct = Math.round((r.coverageAfterPct - r.coverageBeforePct) * 1000) / 10
                return (
                  <div key={r.id} className="px-5 py-4">
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge tone={RISK_TONE[r.risk]}>{r.risk} risk</Badge>
                          <Badge tone="neutral">{r.provider}</Badge>
                          <Badge tone="neutral">{r.termMonths}mo</Badge>
                        </div>
                        <p className="mt-2 text-sm font-medium text-ink">{r.title}</p>
                        <p className="mt-1 text-xs text-ink-muted">{r.summary}</p>
                      </div>
                      <div className="sm:text-right shrink-0">
                        <p className="text-lg font-semibold text-success tabular-nums">
                          {formatCurrency(r.estimatedMonthlySavings)}
                        </p>
                        <p className="text-[11px] text-ink-muted">per month</p>
                        <p className="mt-0.5 text-[11px] text-ink-muted tabular-nums">
                          {formatCurrency(r.estimatedAnnualSavings)} / year
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      <Metric label="Monthly cost" value={formatCurrency(r.estimatedMonthlyCost)} />
                      <Metric label="Coverage" value={`${(r.coverageBeforePct * 100).toFixed(0)}% → ${(r.coverageAfterPct * 100).toFixed(0)}%`} />
                      <Metric label="Coverage delta" value={formatPercent(deltaPct)} positive />
                      <Metric label="Confidence" value={`${(r.confidence * 100).toFixed(0)}%`} />
                    </div>

                    {r.risk === 'BLOCKED' ? (
                      <div className="mt-3 rounded border border-warning-soft bg-warning-soft/60 px-3 py-2 text-xs">
                        <p className="text-ink font-medium">Blocked by policy</p>
                        <ul className="mt-1 list-disc list-inside text-ink-muted space-y-0.5">
                          {r.riskReasons.map((reason, i) => <li key={i}>{reason}</li>)}
                        </ul>
                      </div>
                    ) : canManage ? (
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <Button size="sm" variant="primary" onClick={() => setApproving(r)}>
                          Approve <ArrowRight size={12} />
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => { setRejecting(r); setReason('') }}>
                          Reject
                        </Button>
                      </div>
                    ) : (
                      <p className="mt-3 text-xs text-ink-muted">
                        Your role cannot approve commitment recommendations.
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </CardBody>
      </Card>

      <Modal
        open={approving !== null}
        onClose={() => setApproving(null)}
        title="Approve commitment purchase"
        description="This records a decision. The purchase itself is performed outside CloudFinOps AI."
        footer={
          <>
            <Button variant="ghost" onClick={() => setApproving(null)} disabled={decide.isPending}>
              Cancel
            </Button>
            <Button variant="primary" onClick={confirmApprove} disabled={decide.isPending}>
              {decide.isPending ? (
                <span className="inline-flex items-center gap-1.5">
                  <Loader2 size={13} className="animate-spin" /> Submitting
                </span>
              ) : (
                'Confirm approval'
              )}
            </Button>
          </>
        }
      >
        {approving ? (
          <div className="space-y-2 text-sm">
            <p className="text-ink font-medium">{approving.title}</p>
            <p className="text-xs text-ink-muted">{approving.summary}</p>
            <div className="mt-2 flex items-center gap-3 text-xs">
              <span className="text-ink-muted">
                Savings <span className="text-success font-medium tabular-nums">{formatCurrency(approving.estimatedMonthlySavings)}/mo</span>
              </span>
              <span className="text-ink-muted">
                Term <span className="text-ink">{approving.termMonths} months</span>
              </span>
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal
        open={rejecting !== null}
        onClose={() => { setRejecting(null); setReason('') }}
        title="Reject commitment recommendation"
        description="Provide a reason. It is recorded on the recommendation and in the audit log."
        footer={
          <>
            <Button variant="ghost" onClick={() => { setRejecting(null); setReason('') }} disabled={decide.isPending}>
              Cancel
            </Button>
            <Button variant="danger" onClick={confirmReject} disabled={decide.isPending || !reason.trim()}>
              {decide.isPending ? 'Submitting' : 'Confirm rejection'}
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

function Metric({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">{label}</p>
      <p className={clsx('mt-0.5 tabular-nums', positive ? 'text-success font-medium' : 'text-ink')}>{value}</p>
    </div>
  )
}