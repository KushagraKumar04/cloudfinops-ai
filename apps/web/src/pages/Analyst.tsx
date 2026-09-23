import { useEffect, useRef, useState } from 'react'
import { RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Composer } from '@/features/analyst/Composer'
import { ChatMessage } from '@/features/analyst/ChatMessage'
import { SuggestedQuestions } from '@/features/analyst/SuggestedQuestions'
import { simulateAnalystRun } from '@/features/analyst/mocks'
import type { ChatMessage as ChatMessageType } from '@/features/analyst/types'

function uid(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`
}

export function Analyst() {
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [busy, setBusy] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [messages])

  const send = async (text: string) => {
    const userMsg: ChatMessageType = {
      id: uid('msg'),
      role: 'user',
      text,
      createdAt: new Date().toISOString(),
    }
    const assistantId = uid('msg')
    const assistantMsg: ChatMessageType = {
      id: assistantId,
      role: 'assistant',
      plan: [],
      toolCalls: [],
      status: 'planning',
      createdAt: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg, assistantMsg])
    setBusy(true)

    const patch = (updater: (m: ChatMessageType) => ChatMessageType) =>
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? updater(m) : m)))

    try {
      await simulateAnalystRun(text, (update) => {
        patch((m) => ({
          ...m,
          plan: update.plan ?? m.plan,
          toolCalls: update.toolCall ? [...(m.toolCalls ?? []), update.toolCall] : m.toolCalls,
          response: update.response ?? m.response,
          status: update.status,
        }))
      })
    } catch {
      patch((m) => ({ ...m, status: 'error' }))
    } finally {
      setBusy(false)
    }
  }

  const reset = () => {
    setMessages([])
  }

  return (
    <div className="flex flex-col h-[calc(100vh-6.5rem)]">
      <div className="flex items-center justify-between gap-3 mb-3">
        <div>
          <h1 className="text-xl font-semibold text-ink tracking-tight">AI Analyst</h1>
          <p className="mt-0.5 text-sm text-ink-muted">
            Investigations are planned by the orchestrator and executed by specialized agents.
          </p>
        </div>
        {messages.length > 0 ? (
          <Button variant="ghost" size="sm" onClick={reset} disabled={busy}>
            <RotateCcw size={13} /> New chat
          </Button>
        ) : null}
      </div>

      <div className="flex-1 min-h-0 rounded-md border border-border bg-surface flex flex-col overflow-hidden">
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
          <div className="mx-auto max-w-3xl space-y-6">
            {messages.length === 0 ? (
              <SuggestedQuestions onSelect={send} />
            ) : (
              messages.map((m) => <ChatMessage key={m.id} message={m} onFollowUp={send} />)
            )}
          </div>
        </div>
        <div className="border-t border-border bg-surface">
          <div className="mx-auto max-w-3xl px-4 sm:px-6 py-3">
            <Composer onSend={send} disabled={busy} />
            <p className="mt-2 text-[11px] text-ink-subtle">
              Demo responses use mock data. The orchestrator never executes cloud mutations.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}