import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { USE_MOCKS } from '@/lib/api/client'
import { Composer } from '@/features/analyst/Composer'
import { ChatMessage } from '@/features/analyst/ChatMessage'
import { SuggestedQuestions } from '@/features/analyst/SuggestedQuestions'
import { SessionSidebar } from '@/features/analyst/SessionSidebar'

import { simulateAnalystRun } from '@/features/analyst/mocks'
import { useCreateSession, useSession } from '@/features/analyst/sessionHooks'
import { streamChat } from '@/features/analyst/streamClient'
import type { ChatMessage as ChatMessageType, ToolCall } from '@/features/analyst/types'
import type { ChatSessionMessage } from '@/features/analyst/sessionTypes'

function uid(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`
}

function sessionMessageToChat(m: ChatSessionMessage): ChatMessageType {
  if (m.role === 'user') {
    return {
      id: m.id,
      role: 'user',
      text: m.content,
      createdAt: m.createdAt,
    }
  }
  const payload = m.responsePayload as ChatMessageType['response']
  return {
    id: m.id,
    role: 'assistant',
    plan: m.plan,
    toolCalls: m.toolCalls as unknown as ToolCall[],
    response: payload && 'answer' in payload ? { ...payload, source: m.source } : undefined,
    status: 'complete',
    createdAt: m.createdAt,
  }
}

export function Analyst() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [busy, setBusy] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const streamingRef = useRef(false)
  const qc = useQueryClient()

  const createSession = useCreateSession()
  const sessionDetail = useSession(activeSessionId ?? undefined)

  useEffect(() => {
    if (streamingRef.current) return
    if (!activeSessionId) return
    if (!sessionDetail.data) return
    const restored = sessionDetail.data.messages.map(sessionMessageToChat)
    setMessages(restored)
  }, [activeSessionId, sessionDetail.data])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [messages])

  const ensureSession = async (): Promise<string> => {
    if (activeSessionId) return activeSessionId
    const created = await createSession.mutateAsync(undefined)
    setActiveSessionId(created.id)
    return created.id
  }

  const sendMock = async (text: string) => {
    const userMsg: ChatMessageType = { id: uid('msg'), role: 'user', text, createdAt: new Date().toISOString() }
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

  const sendLive = async (text: string) => {
    const sessionId = await ensureSession()
    const userMsg: ChatMessageType = { id: uid('msg'), role: 'user', text, createdAt: new Date().toISOString() }
    const assistantId = uid('msg')
    const assistantMsg: ChatMessageType = {
      id: assistantId,
      role: 'assistant',
      plan: [],
      toolCalls: [],
      status: 'planning',
      createdAt: new Date().toISOString(),
    }
    streamingRef.current = true
    setMessages((prev) => [...prev, userMsg, assistantMsg])
    setBusy(true)

    const patch = (updater: (m: ChatMessageType) => ChatMessageType) =>
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? updater(m) : m)))

    try {
      let streamed = ''
      await streamChat({
        sessionId,
        message: text,
        onEvent: (event) => {
          if (event.type === 'planning') {
            patch((m) => ({ ...m, status: 'planning' }))
          } else if (event.type === 'plan') {
            patch((m) => ({ ...m, plan: event.steps, status: 'running' }))
          } else if (event.type === 'tool') {
            const normalizedArgs: Record<string, string | number | undefined> = {}
            for (const [key, value] of Object.entries(event.args)) {
              normalizedArgs[key] = typeof value === 'string' || typeof value === 'number' ? value : String(value)
            }
            patch((m) => ({
              ...m,
              toolCalls: [
                ...(m.toolCalls ?? []),
                {
                  id: event.id,
                  name: event.name,
                  args: normalizedArgs,
                  resultSummary: event.resultSummary,
                  durationMs: event.durationMs,
                },
              ],
            }))
          } else if (event.type === 'answer_start') {
            streamed = ''
            patch((m) => ({ ...m, response: { ...(m.response ?? { findings: [], evidence: [], recommendations: [], confidence: 0, requires_human_review: false }), answer: '' } }))
          } else if (event.type === 'token') {
            streamed += event.text
            const current = streamed
            patch((m) => ({
              ...m,
              response: {
                findings: m.response?.findings ?? [],
                evidence: m.response?.evidence ?? [],
                recommendations: m.response?.recommendations ?? [],
                confidence: m.response?.confidence ?? 0,
                requires_human_review: m.response?.requires_human_review ?? false,
                followUps: m.response?.followUps,
                source: m.response?.source,
                answer: current,
              },
            }))
          } else if (event.type === 'done') {
            patch((m) => ({
              ...m,
              response: { ...event.response, source: event.source, llmError: event.llmError },
              status: 'complete',
            }))
          } else if (event.type === 'error') {
            patch((m) => ({ ...m, status: 'error' }))
          }
        },
      })
    } catch {
      patch((m) => ({ ...m, status: 'error' }))
    } finally {
      streamingRef.current = false
      setBusy(false)
      if (sessionId) {
        qc.invalidateQueries({ queryKey: ['chatSessions', 'list'] })
        qc.invalidateQueries({ queryKey: ['chatSessions', 'detail', sessionId] })
      }
    }
  }

  const send = USE_MOCKS ? sendMock : sendLive

  const reset = async () => {
    setActiveSessionId(null)
    setMessages([])
    qc.removeQueries({ queryKey: ['chatSessions', 'detail'] })
    const created = await createSession.mutateAsync(undefined)
    setActiveSessionId(created.id)
  }

  const selectSession = (id: string) => {
    if (id === activeSessionId) return
    setActiveSessionId(id)
    setMessages([])
  }

  const handleSessionDeleted = (id: string) => {
    if (id === activeSessionId) {
      setActiveSessionId(null)
      setMessages([])
    }
    qc.removeQueries({ queryKey: ['chatSessions', 'detail', id] })
  }

  return (
    <div className="flex h-[calc(100vh-6.5rem)] -mx-4 sm:-mx-6 lg:-mx-8">
      {!USE_MOCKS ? (
        <SessionSidebar
          activeSessionId={activeSessionId}
          onSelect={selectSession}
          onNew={reset}
          onDeleted={handleSessionDeleted}
        />
      ) : null}
      <div className="flex flex-1 flex-col min-w-0 px-4 sm:px-6 lg:px-8">
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
                Investigations return structured evidence. The orchestrator never executes cloud mutations.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}