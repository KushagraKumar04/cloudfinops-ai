import { useState } from 'react'
import { ChevronDown, ChevronRight, Wrench } from 'lucide-react'
import { clsx } from 'clsx'
import type { AssistantStatus, ToolCall } from './types'

interface Props {
  plan?: string[]
  toolCalls?: ToolCall[]
  status: AssistantStatus
}

export function ToolCallTrace({ plan, toolCalls, status }: Props) {
  const [open, setOpen] = useState(true)
  const hasPlan = plan && plan.length > 0
  const hasCalls = toolCalls && toolCalls.length > 0
  if (!hasPlan && !hasCalls && status === 'complete') return null

  const totalMs = (toolCalls ?? []).reduce((s, c) => s + c.durationMs, 0)
  const callCount = toolCalls?.length ?? 0

  return (
    <div className="rounded-md border border-border bg-surface-muted/40">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 px-3.5 py-2 text-left"
      >
        <span className="flex items-center gap-2 text-xs font-medium text-ink-muted">
          {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          <span>Investigation</span>
          <span className="text-ink-subtle">·</span>
          <span className="text-ink-subtle">
            {callCount} tool{callCount === 1 ? '' : 's'} · {Math.round(totalMs)} ms
          </span>
          {status !== 'complete' ? (
            <span className="ml-1 inline-flex items-center gap-1 text-[11px] text-accent">
              <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
              {status === 'planning' ? 'planning' : 'running'}
            </span>
          ) : null}
        </span>
      </button>
      {open ? (
        <div className="border-t border-border px-3.5 py-3 space-y-3">
          {hasPlan ? (
            <div>
              <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Plan</p>
              <ol className="mt-1.5 space-y-1 text-xs text-ink-muted">
                {plan!.map((p, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-ink-subtle tabular-nums">{i + 1}.</span>
                    <span>{p}</span>
                  </li>
                ))}
              </ol>
            </div>
          ) : null}
          {hasCalls ? (
            <div>
              <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Tool calls</p>
              <ul className="mt-1.5 space-y-1.5">
                {toolCalls!.map((c) => (
                  <li key={c.id} className="flex items-start gap-2 text-xs">
                    <Wrench size={11} className="mt-0.5 shrink-0 text-ink-subtle" />
                    <div className="min-w-0">
                      <p className="text-ink font-mono text-[11px]">{c.name}</p>
                      {Object.keys(c.args).length > 0 ? (
                        <p className="text-[11px] text-ink-subtle font-mono truncate">
                          {Object.entries(c.args)
                            .map(([k, v]) => `${k}=${String(v)}`)
                            .join(' ')}
                        </p>
                      ) : null}
                      <p className={clsx('text-ink-muted mt-0.5')}>{c.resultSummary}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}