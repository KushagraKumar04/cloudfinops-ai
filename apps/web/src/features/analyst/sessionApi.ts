import { request, USE_MOCKS, withMockDelay } from '@/lib/api/client'
import type {
  ChatSessionDetail,
  ChatSessionListResult,
  ChatSessionSummary,
} from './sessionTypes'

export async function listSessions(): Promise<ChatSessionListResult> {
  if (USE_MOCKS) return withMockDelay({ items: [], total: 0 })
  return request<ChatSessionListResult>('/chat/sessions')
}

export async function createSession(title?: string): Promise<ChatSessionSummary> {
  if (USE_MOCKS) {
    return withMockDelay({
      id: `sess_${Math.random().toString(36).slice(2, 10)}`,
      title: title ?? 'New conversation',
      messageCount: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    })
  }
  return request<ChatSessionSummary>('/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({ title: title ?? null }),
  })
}

export async function getSession(id: string): Promise<ChatSessionDetail> {
  if (USE_MOCKS) throw new Error('Sessions are not available in mock mode')
  return request<ChatSessionDetail>(`/chat/sessions/${id}`)
}

export async function deleteSession(id: string): Promise<void> {
  if (USE_MOCKS) return withMockDelay(undefined)
  await request<void>(`/chat/sessions/${id}`, { method: 'DELETE' })
}