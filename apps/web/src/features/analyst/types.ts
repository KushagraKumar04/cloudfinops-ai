export type Severity = 'info' | 'warning' | 'critical'
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'BLOCKED'
export type ChatRole = 'user' | 'assistant'
export type AssistantStatus = 'planning' | 'running' | 'complete' | 'error'

export interface AnalystFinding {
  severity: Severity
  title: string
  detail: string
}

export interface AnalystEvidence {
  label: string
  value: string
  source: string
}

export interface AnalystRecommendationRef {
  id: string
  title: string
  estimatedMonthlySavings: number
  risk: RiskLevel
}

export interface AnalystResponse {
  answer: string
  findings: AnalystFinding[]
  evidence: AnalystEvidence[]
  recommendations: AnalystRecommendationRef[]
  confidence: number
  requires_human_review: boolean
  followUps?: string[]
  source?: 'llm' | 'rules'
  llmError?: string | null
}

export interface ToolCall {
  id: string
  name: string
  args: Record<string, string | number | undefined>
  resultSummary: string
  durationMs: number
}

export interface ChatMessage {
  id: string
  role: ChatRole
  text?: string
  plan?: string[]
  toolCalls?: ToolCall[]
  response?: AnalystResponse
  status?: AssistantStatus
  createdAt: string
}

export function confidenceLabel(c: number): 'HIGH' | 'MEDIUM' | 'LOW' {
  if (c >= 0.85) return 'HIGH'
  if (c >= 0.65) return 'MEDIUM'
  return 'LOW'
}