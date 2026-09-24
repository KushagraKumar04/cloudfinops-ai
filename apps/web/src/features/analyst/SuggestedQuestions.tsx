import { Sparkles, ArrowUpRight } from 'lucide-react'
import { SUGGESTED_QUESTIONS } from './mocks'

export function SuggestedQuestions({ onSelect }: { onSelect: (q: string) => void }) {
  return (
    <div className="mx-auto max-w-2xl text-center py-8">
      <div className="inline-flex items-center justify-center h-9 w-9 rounded-full border border-border bg-surface text-accent">
        <Sparkles size={16} />
      </div>
      <h2 className="mt-4 text-lg font-semibold text-ink">Ask the FinOps analyst</h2>
      <p className="mt-1 text-sm text-ink-muted max-w-lg mx-auto">
        The orchestrator plans an investigation, calls specialized agents, and returns an evidence-backed answer. Cloud mutations always require human approval.
      </p>
      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
        {SUGGESTED_QUESTIONS.map((q) => (
          <button
            key={q}
            onClick={() => onSelect(q)}
            className="group flex items-start justify-between gap-2 rounded-md border border-border bg-surface px-3.5 py-2.5 text-left text-sm text-ink hover:border-border-strong transition-colors"
          >
            <span>{q}</span>
            <ArrowUpRight size={14} className="mt-0.5 shrink-0 text-ink-subtle group-hover:text-ink" />
          </button>
        ))}
      </div>
      <p className="mt-6 text-[11px] text-ink-subtle">
        Responses are generated from demo data. No cloud API calls are made.
      </p>
    </div>
  )
}