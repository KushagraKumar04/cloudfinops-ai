import { API_BASE_URL } from '@/lib/api/client'
import type { StreamEvent } from './sessionTypes'

export interface StreamOptions {
  sessionId: string
  message: string
  signal?: AbortSignal
  onEvent: (event: StreamEvent) => void
}

function parseEventBlock(block: string): StreamEvent | null {
  const lines = block.split('\n')
  let eventName = ''
  let dataLine = ''
  for (const line of lines) {
    if (line.startsWith('event:')) eventName = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLine += line.slice(5).trim()
  }
  if (!eventName) return null
  let payload: Record<string, unknown> = {}
  if (dataLine) {
    try {
      payload = JSON.parse(dataLine)
    } catch {
      payload = {}
    }
  }
  switch (eventName) {
    case 'user_ack':
      return { type: 'user_ack', messageId: String(payload.messageId ?? ''), sessionTitle: String(payload.sessionTitle ?? '') }
    case 'planning':
      return { type: 'planning' }
    case 'plan':
      return { type: 'plan', steps: (payload.steps as string[]) ?? [] }
    case 'tool':
      return {
        type: 'tool',
        id: String(payload.id ?? ''),
        name: String(payload.name ?? ''),
        args: (payload.args as Record<string, unknown>) ?? {},
        resultSummary: String(payload.resultSummary ?? ''),
        durationMs: Number(payload.durationMs ?? 0),
      }
    case 'answer_start':
      return { type: 'answer_start' }
    case 'token':
      return { type: 'token', text: String(payload.text ?? '') }
    case 'answer_end':
      return { type: 'answer_end' }
    case 'done':
      return {
        type: 'done',
        response: (payload.response as never) ?? ({} as never),
        source: (payload.source as 'llm' | 'rules') ?? 'rules',
        intent: String(payload.intent ?? 'generic'),
        llmError: (payload.llmError as string | null) ?? null,
      }
    case 'error':
      return { type: 'error', message: String(payload.message ?? 'Stream error') }
    default:
      return null
  }
}

export async function streamChat({ sessionId, message, signal, onEvent }: StreamOptions): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat/sessions/${sessionId}/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ message }),
    signal,
  })

  if (!response.ok || !response.body) {
    throw new Error(`Stream failed with status ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let sep = buffer.indexOf('\n\n')
    while (sep !== -1) {
      const block = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      const event = parseEventBlock(block)
      if (event) onEvent(event)
      sep = buffer.indexOf('\n\n')
    }
  }
}