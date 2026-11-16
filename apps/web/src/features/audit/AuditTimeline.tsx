import {
  Cloud,
  RefreshCw,
  Server,
  ShieldAlert,
  Lightbulb,
  Play,
  ScrollText,
  KeyRound,
  AlertTriangle,
  Info,
  type LucideIcon,
} from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { formatDateTime } from '@/lib/format'
import { CATEGORY_LABEL } from './queryParams'
import type { AuditCategory, AuditEvent, AuditSeverity } from './types'

const CATEGORY_ICON: Record<AuditCategory, LucideIcon> = {
  'cloud.account': Cloud,
  'billing.sync': RefreshCw,
  resource: Server,
  'cost.anomaly': ShieldAlert,
  recommendation: Lightbulb,
  execution: Play,
  policy: ScrollText,
  auth: KeyRound,
}

const SEVERITY_TONE: Record<AuditSeverity, 'neutral' | 'warning' | 'danger'> = {
  info: 'neutral',
  warning: 'warning',
  critical: 'danger',
}

const SEVERITY_ICON: Record<AuditSeverity, LucideIcon | null> = {
  info: null,
  warning: AlertTriangle,
  critical: AlertTriangle,
}

export function AuditTimeline({ events }: { events: AuditEvent[] }) {
  return (
    <ol className="relative">
      {events.map((e, i) => {
        const Icon = CATEGORY_ICON[e.category]
        const SevIcon = SEVERITY_ICON[e.severity]
        const last = i === events.length - 1
        return (
          <li key={e.id} className="relative pl-10 pb-6 last:pb-0">
            {!last ? (
              <span className="absolute left-[15px] top-7 bottom-0 w-px bg-border" aria-hidden />
            ) : null}
            <span className="absolute left-0 top-0.5 flex h-[30px] w-[30px] items-center justify-center rounded-full border border-border bg-surface">
              <Icon size={14} className="text-ink-muted" strokeWidth={1.75} />
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-ink">{e.action}</span>
                {SevIcon ? <SevIcon size={12} className={e.severity === 'critical' ? 'text-danger' : 'text-warning'} /> : <Info size={12} className="text-ink-subtle" />}
                <Badge tone={SEVERITY_TONE[e.severity]}>{e.severity}</Badge>
                <Badge tone="neutral">{CATEGORY_LABEL[e.category]}</Badge>
              </div>
              <p className="mt-1 text-sm text-ink-muted">{e.subject}</p>
              <p className="mt-1 text-xs text-ink-muted leading-relaxed">{e.details}</p>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-ink-subtle">
                <span>{formatDateTime(e.at)}</span>
                <span>·</span>
                <span className="font-mono">{e.actor}</span>
                <span>·</span>
                <span className="font-mono">{e.id}</span>
              </div>
              {e.metadata.length > 0 ? (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {e.metadata.map((m) => (
                    <span
                      key={m.key}
                      className="inline-flex items-center gap-1 rounded border border-border bg-surface-muted px-2 py-0.5 text-[10px] font-mono"
                    >
                      <span className="text-ink-muted">{m.key}</span>
                      <span className="text-ink-subtle">=</span>
                      <span className="text-ink">{m.value}</span>
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          </li>
        )
      })}
    </ol>
  )
}