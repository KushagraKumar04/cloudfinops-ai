import type { AnalystResponse, ToolCall } from './types'

export interface ChatSessionSummary {
  id: string
  title: string
  messageCount: number
  createdAt: string
  updatedAt: string
}

export interface ChatSessionMessage {
  id: string
  sessionId: string
  role: 'user' | 'assistant' | 'system'
  content: string
  responsePayload: AnalystResponse | Record<string, never>
  plan: string[]
  toolCalls: ToolCall[]
  source: 'llm' | 'rules'
  intent: string
  createdAt: string
}

export interface ChatSessionDetail extends ChatSessionSummary {
  messages: ChatSessionMessage[]
}

export interface ChatSessionListResult {
  items: ChatSessionSummary[]
  total: number
}

export type StreamEvent =
  | { type: 'user_ack'; messageId: string; sessionTitle: string }
  | { type: 'planning' }
  | { type: 'plan'; steps: string[] }
  | { type: 'tool'; id: string; name: string; args: Record<string, unknown>; resultSummary: string; durationMs: number }
  | { type: 'answer_start' }
  | { type: 'token'; text: string }
  | { type: 'answer_end' }
  | { type: 'done'; response: AnalystResponse; source: 'llm' | 'rules'; intent: string; llmError?: string | null }
  | { type: 'error'; message: string }