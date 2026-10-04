import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, ExternalLink } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { KpiCard } from '@/components/ui/KpiCard'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { formatCurrency, formatDateTime } from '@/lib/format'
import { RiskBadge, StatusBadge } from '@/features/recommendations/badges'
import { ExecutionPanel } from '@/features/executions/ExecutionPanel'
import { useAuth } from '@/features/auth/useAuth'
import { useRecommendation, useRecommendationDecision } from '@/features/recommendations/hooks'
import { confidenceLabel } from '@/features/recommendations/types'
import type { RecommendationDecision } from '@/features/recommendations/types'

export function RecommendationDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data, isLoading, isError, refetch } = useRecommendation(id)
  const decide = useRecommendationDecision(id ?? '')
  const [pendingAction, setPendingAction] = useState<RecommendationDecision['action'] | null>(null)
  const [reason, setReason] = useState('')
  const { can } = useAuth()

  if (isLoading) {
    return (
      <>
        <Skeleton className="h-6 w-40 mb-4" />
        <Skeleton className="h-32 w-full" />
        <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Skeleton className="lg:col-span-2 h-64" />
          <Skeleton className="h-64" />
        </div>
      </>
    )
  }

  if (isError || !data) {
    return (
      <Card>
        <StateBlock
          variant="error"
          title="Recommendation not found"
          description="The recommendation may have been removed or the ID is invalid."
          action={
            <div className="flex gap-2">
              <Button size="sm" onClick={() => refetch()}>Retry</Button>
              <Button size="sm" variant="ghost" onClick={() => navigate('/recommendations')}>Back to list</Button>
            </div>
          }
        />
      </Card>
    )
  }

  const isPending = data.status === 'pending'
  const isBlocked = data.risk === 'BLOCKED'

  const onConfirm = () => {
    if (!pendingAction) return
    if (pendingAction === 'reject' && !reason.trim()) return
    decide.mutate(
      { action: pendingAction, reason: reason.trim() || undefined },
      {
        onSuccess: () => {
          setPendingAction(null)
          setReason('')
        },
      },
    )
  }

  const closeModal = () => {
    setPendingAction(null)
    setReason('')
  }

  const modalTitle =
    pendingAction === 'approve'
      ? 'Approve recommendation'
      : pendingAction === 'reject'
        ? 'Reject recommendation'
        : 'Defer recommendation'

  const modalDescription =
    pendingAction === 'approve'
      ? 'Approving this recommendation creates an execution plan but does not mutate any cloud resource. Execution requires a separate policy check and dry run.'
      : pendingAction === 'reject'
        ? 'Provide a reason. The reason is stored on the recommendation and shown in the audit log.'
        : 'Deferring keeps the recommendation open. Provide context for later review.'

  return (
    <>
      <div className="mb-3">
        <Link to="/recommendations" className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink">
          <ArrowLeft size={13} /> Recommendations
        </Link>
      </div>

      <PageHeader
        title={data.title}
        description={`${data.typeLabel} · ${data.resourceName} · ${data.accountName}`}
        action={
          <div className="flex items-center gap-2">
            <RiskBadge risk={data.risk} />
            <StatusBadge status={data.status} />
          </div>
        }
      />

      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard label="Current monthly cost" value={formatCurrency(data.currentMonthlyCost)} hint="observed" />
        <KpiCard label="Estimated monthly cost" value={formatCurrency(data.estimatedMonthlyCost)} hint="after change" />
        <KpiCard
          label="Estimated savings"
          value={formatCurrency(data.estimatedMonthlySavings)}
          delta={`${formatCurrency(data.estimatedMonthlySavings * 12)} / yr`}
          deltaTone="success"
          hint="deterministic"
        />
        <KpiCard
          label="Confidence"
          value={confidenceLabel(data.confidence)}
          hint={`${Math.round(data.confidence * 100)}% · metric coverage`}
        />
      </section>

      <section className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader title="Summary" subtitle="What is being proposed and why" />
            <CardBody>
              <p className="text-sm text-ink leading-relaxed">{data.summary}</p>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Current vs proposed state" />
            <CardBody className="p-0">
              <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-border">
                <div className="p-5">
                  <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Current</p>
                  <dl className="mt-3 space-y-2">
                    {data.currentState.map((s) => (
                      <div key={s.key} className="flex items-baseline justify-between gap-3">
                        <dt className="text-xs text-ink-muted">{s.key}</dt>
                        <dd className="text-sm text-ink tabular-nums">{s.value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
                <div className="p-5 bg-surface-muted/40">
                  <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Proposed</p>
                  <dl className="mt-3 space-y-2">
                    {data.proposedState.map((s) => (
                      <div key={s.key} className="flex items-baseline justify-between gap-3">
                        <dt className="text-xs text-ink-muted">{s.key}</dt>
                        <dd className="text-sm text-ink tabular-nums">{s.value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Evidence" subtitle="Facts retrieved from provider APIs and metric stores" />
            <CardBody className="p-0">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-ink-muted">
                    <th className="px-5 py-2 font-medium">Metric</th>
                    <th className="px-5 py-2 font-medium">Value</th>
                    <th className="px-5 py-2 font-medium">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {data.evidence.map((e) => (
                    <tr key={e.label} className="border-b border-border last:border-b-0">
                      <td className="px-5 py-2.5 text-ink-muted">{e.label}</td>
                      <td className="px-5 py-2.5 text-ink tabular-nums">{e.value}</td>
                      <td className="px-5 py-2.5 text-ink-subtle">{e.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Implementation plan" subtitle="Sequenced actions and verification steps" />
            <CardBody>
              <ol className="space-y-2.5">
                {data.implementationPlan.map((step, i) => (
                  <li key={i} className="flex gap-3 text-sm">
                    <span className="shrink-0 inline-flex h-5 w-5 items-center justify-center rounded-full border border-border text-[11px] text-ink-muted tabular-nums">
                      {i + 1}
                    </span>
                    <span className="text-ink leading-relaxed">{step}</span>
                  </li>
                ))}
              </ol>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Approval" subtitle="Human approval is required before any mutation is executed" />
            <CardBody>
              {!isPending ? (
                <div className="space-y-3">
                  <p className="text-sm text-ink">
                    This recommendation is <span className="font-medium">{data.status}</span>. No further action is required from you.
                  </p>
                  {data.history.length > 0 ? (
                    <ul className="space-y-1.5 text-xs text-ink-muted">
                      {data.history.slice(-3).map((h, i) => (
                        <li key={i}>
                          <span className="text-ink-subtle">{formatDateTime(h.at)}</span> · {h.actor} · {h.action}
                          {h.reason ? <span className="text-ink-subtle"> — “{h.reason}”</span> : null}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : isBlocked ? (
                <div className="rounded border border-warning-soft bg-warning-soft/60 px-4 py-3 text-sm text-ink">
                  Policy blocked this recommendation from approval. Resolve the blocking reasons before proceeding.
                  <ul className="mt-2 space-y-1 text-xs text-ink-muted list-disc list-inside">
                    {data.riskReasons.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ul>
                </div>
              ) : !can('approve_recommendation') ? (
                <p className="text-sm text-ink-muted">
                  Your role does not allow approving recommendations. Contact an admin.
                </p>
              ) : (
                <div className="flex flex-col gap-3">
                  <p className="text-xs text-ink-muted">
                    Approving creates an execution plan. Execution is a separate step gated by the policy engine, a dry run, and re-validation of resource state.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <Button variant="primary" size="md" onClick={() => setPendingAction('approve')}>
                      Approve
                    </Button>
                    <Button variant="secondary" size="md" onClick={() => setPendingAction('reject')}>
                      Reject
                    </Button>
                    <Button variant="ghost" size="md" onClick={() => setPendingAction('defer')}>
                      Defer
                    </Button>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>
        </div>

        <div className="space-y-4">
          <ExecutionPanel recommendationId={data.id} status={data.status} />

          <Card>
            <CardHeader title="Risk & impact" />
            <CardBody className="space-y-3">
              <div className="flex items-center gap-2">
                <RiskBadge risk={data.risk} />
                {data.riskReasons.map((r) => (
                  <span key={r} className="text-[11px] text-ink-muted">{r}</span>
                ))}
              </div>
              <div className="pt-2 space-y-2.5">
                <Impact label="Availability" value={data.impact.availability} />
                <Impact label="Security" value={data.impact.security} />
                <Impact label="Operational" value={data.impact.operational} />
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Savings calculation" subtitle="Deterministic inputs and basis" />
            <CardBody className="space-y-3">
              <div className="flex items-baseline justify-between">
                <span className="text-xs text-ink-muted">Current</span>
                <span className="text-sm text-ink tabular-nums">{formatCurrency(data.currentMonthlyCost)}</span>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-xs text-ink-muted">Proposed</span>
                <span className="text-sm text-ink tabular-nums">{formatCurrency(data.estimatedMonthlyCost)}</span>
              </div>
              <div className="flex items-baseline justify-between border-t border-border pt-2">
                <span className="text-xs font-medium text-ink">Savings</span>
                <span className="text-sm font-semibold text-success tabular-nums">
                  {formatCurrency(data.estimatedMonthlySavings)} / mo
                </span>
              </div>
              <div className="pt-2">
                <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Calculation basis</p>
                <ul className="mt-1.5 space-y-1 text-xs text-ink-muted list-disc list-inside">
                  {data.calculationBasis.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Resource" />
            <CardBody className="space-y-2 text-sm">
              <div>
                <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Name</p>
                <p className="mt-0.5 text-ink">{data.resourceName}</p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Field label="Type" value={data.resourceType} />
                <Field label="Provider" value={data.provider} />
                <Field label="Region" value={data.region} />
                <Field label="Environment" value={data.environment} />
              </div>
              <Link
                to={`/resources/${data.resourceId}`}
                className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-accent hover:underline"
              >
                Open resource <ExternalLink size={12} />
              </Link>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="History" />
            <CardBody className="space-y-3">
              <ol className="space-y-3">
                {data.history.map((h, i) => (
                  <li key={i} className="text-xs">
                    <div className="flex items-center gap-2">
                      <span className="text-ink font-medium">{h.action}</span>
                      <span className="text-ink-subtle">·</span>
                      <span className="text-ink-subtle">{h.actor}</span>
                    </div>
                    <p className="mt-0.5 text-ink-muted">{formatDateTime(h.at)}</p>
                    {h.reason ? <p className="mt-1 text-ink-muted">“{h.reason}”</p> : null}
                  </li>
                ))}
              </ol>
            </CardBody>
          </Card>
        </div>
      </section>

      <Modal
        open={pendingAction !== null}
        onClose={closeModal}
        title={modalTitle}
        description={modalDescription}
        footer={
          <>
            <Button variant="ghost" onClick={closeModal} disabled={decide.isPending}>
              Cancel
            </Button>
            <Button
              variant={pendingAction === 'reject' ? 'danger' : 'primary'}
              onClick={onConfirm}
              disabled={decide.isPending || (pendingAction === 'reject' && !reason.trim())}
            >
              {decide.isPending ? 'Submitting…' : pendingAction === 'approve' ? 'Confirm approval' : pendingAction === 'reject' ? 'Confirm rejection' : 'Confirm deferral'}
            </Button>
          </>
        }
      >
        {pendingAction === 'reject' ? (
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
        ) : pendingAction === 'defer' ? (
          <label className="block">
            <span className="text-xs font-medium text-ink">Context (optional)</span>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              className="mt-1.5 w-full rounded border border-border bg-surface px-3 py-2 text-sm focus:border-accent focus:outline-none"
              placeholder="Any context for the next review"
            />
          </label>
        ) : (
          <p className="text-sm text-ink-muted">
            This action records a decision. No cloud resource will be modified. Execution is a separate, policy-gated step.
          </p>
        )}
      </Modal>
    </>
  )
}

function Impact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">{label}</p>
      <p className="mt-0.5 text-xs text-ink leading-relaxed">{value}</p>
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">{label}</p>
      <p className="mt-0.5 text-sm text-ink capitalize">{value}</p>
    </div>
  )
}