import { request, USE_MOCKS, withMockDelay } from '@/lib/api/client'
import type { AnalystResponse, ToolCall } from './types'

export interface ChatRunResponse {
  answer: string
  plan: string[]
  toolCalls: ToolCall[]
  findings: AnalystResponse['findings']
  evidence: AnalystResponse['evidence']
  recommendations: AnalystResponse['recommendations']
  confidence: number
  requiresHumanReview: boolean
  followUps: string[] | null
  intent: string
  source: 'llm' | 'rules'
  llmError: string | null
  runId: string
}

export async function sendChatMessage(message: string): Promise<ChatRunResponse> {
  if (USE_MOCKS) {
    return withMockDelay({
      answer: 'Mock mode: switch VITE_USE_MOCKS=false to use the real endpoint.',
      plan: [],
      toolCalls: [],
      findings: [],
      evidence: [],
      recommendations: [],
      confidence: 0.5,
      requiresHumanReview: false,
      followUps: null,
      intent: 'generic',
      source: 'rules',
      llmError: null,
      runId: '',
    })
  }
  return request<ChatRunResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}