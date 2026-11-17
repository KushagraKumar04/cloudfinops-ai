import { Link } from 'react-router-dom'
import { AlertTriangle, Info, ShieldAlert, ArrowRight } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { formatCurrency } from '@/lib/format'
import { confidenceLabel, type AnalystResponse, type Severity } from './types'

const SEVERITY_ICON: Record<Severity, typeof Info> = {
  info: Info,
  warning: AlertTriangle,
  critical: ShieldAlert,
}

const SEVERITY_TONE: Record<Severity, string> = {
  info: 'text-ink-subtle',
  warning: 'text-warning',
  critical: 'text-danger',
}

export function StructuredResponse({ response, onFollowUp }: { response: AnalystResponse; onFollowUp: (q: string) => void }) {
  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <p className="text-sm text-ink leading-relaxed whitespace-pre-line">{response.answer}</p>
      </div>

      {response.findings.length > 0 ? (
        <div>
          <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Findings</p>
          <ul className="mt-2 space-y-2">
            {response.findings.map((f, i) => {
              const Icon = SEVERITY_ICON[f.severity]
              return (
                <li key={i} className="flex items-start gap-2.5">
                  <Icon size={14} className={`mt-0.5 shrink-0 ${SEVERITY_TONE[f.severity]}`} />
                  <div>
                    <p className="text-sm text-ink font-medium">{f.title}</p>
                    <p className="mt-0.5 text-xs text-ink-muted leading-relaxed">{f.detail}</p>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      ) : null}

      {response.evidence.length > 0 ? (
        <div>
          <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Evidence</p>
          <div className="mt-2 rounded border border-border overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-surface-muted/50 text-left text-[10px] uppercase tracking-wide text-ink-muted">
                  <th className="px-3 py-1.5 font-medium">Metric</th>
                  <th className="px-3 py-1.5 font-medium">Value</th>
                  <th className="px-3 py-1.5 font-medium">Source</th>
                </tr>
              </thead>
              <tbody>
                {response.evidence.map((e, i) => (
                  <tr key={i} className="border-t border-border">
                    <td className="px-3 py-1.5 text-ink-muted">{e.label}</td>
                    <td className="px-3 py-1.5 text-ink tabular-nums">{e.value}</td>
                    <td className="px-3 py-1.5 text-ink-subtle">{e.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {response.recommendations.length > 0 ? (
        <div>
          <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Linked recommendations</p>
          <ul className="mt-2 space-y-1.5">
            {response.recommendations.map((r) => (
              <li key={r.id}>
                <Link
                  to={`/recommendations/${r.id}`}
                  className="group flex items-center justify-between gap-3 rounded border border-border bg-surface px-3 py-2 hover:border-border-strong transition-colors"
                >
                  <div className="min-w-0">
                    <p className="text-sm text-ink truncate">{r.title}</p>
                    <div className="mt-0.5 flex items-center gap-2">
                      <Badge tone={r.risk === 'HIGH' || r.risk === 'BLOCKED' ? 'danger' : r.risk === 'MEDIUM' ? 'warning' : 'success'}>
                        {r.risk}
                      </Badge>
                      <span className="text-xs text-ink-muted tabular-nums">
                        {formatCurrency(r.estimatedMonthlySavings)} / mo
                      </span>
                    </div>
                  </div>
                  <ArrowRight size={14} className="shrink-0 text-ink-subtle group-hover:text-ink" />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-3 pt-1">
        <span className="text-[11px] text-ink-muted">
          Confidence <span className="text-ink font-medium">{confidenceLabel(response.confidence)}</span>{' '}
          <span className="tabular-nums">({Math.round(response.confidence * 100)}%)</span>
        </span>
        {response.source === 'llm' ? <Badge tone="accent">LLM</Badge> : null}
        {response.source === 'rules' ? <Badge tone="neutral">Rules engine</Badge> : null}
        {response.requires_human_review ? <Badge tone="warning">Requires human review</Badge> : null}
      </div>

      {response.source === 'rules' && response.llmError ? (
        <div className="rounded border border-warning-soft bg-warning-soft/60 px-3 py-2 text-xs text-ink">
          <p className="font-medium">LLM unavailable — using rules engine</p>
          <p className="mt-0.5 text-ink-muted">{response.llmError}</p>
        </div>
      ) : null}

      {response.followUps && response.followUps.length > 0 ? (
        <div>
          <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Follow-ups</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {response.followUps.map((f) => (
              <button
                key={f}
                onClick={() => onFollowUp(f)}
                className="rounded border border-border bg-surface px-2.5 py-1 text-xs text-ink-muted hover:text-ink hover:border-border-strong transition-colors"
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}