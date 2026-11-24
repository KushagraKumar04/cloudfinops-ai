import { request, USE_MOCKS, withMockDelay } from '@/lib/api/client'
import { MOCK_COMMITMENTS, MOCK_COVERAGE_SUMMARY, MOCK_RECOMMENDATIONS } from './mocks'
import type {
  CommitmentListResult,
  CommitmentRecommendation,
  CommitmentRecommendationListResult,
  CoverageSummary,
} from './types'

export async function getCoverageSummary(provider?: string): Promise<CoverageSummary> {
  if (USE_MOCKS) return withMockDelay(MOCK_COVERAGE_SUMMARY)
  const qs = provider && provider !== 'all' ? `?provider=${provider}` : ''
  return request<CoverageSummary>(`/commitments/summary${qs}`)
}

export async function listCommitments(provider?: string): Promise<CommitmentListResult> {
  if (USE_MOCKS) return withMockDelay(MOCK_COMMITMENTS)
  const qs = provider && provider !== 'all' ? `?provider=${provider}` : ''
  return request<CommitmentListResult>(`/commitments${qs}`)
}

export async function listCommitmentRecommendations(
  status = 'pending',
  provider?: string,
): Promise<CommitmentRecommendationListResult> {
  if (USE_MOCKS) return withMockDelay(MOCK_RECOMMENDATIONS)
  const params = new URLSearchParams()
  if (status !== 'all') params.set('status', status)
  if (provider && provider !== 'all') params.set('provider', provider)
  const qs = params.toString()
  return request<CommitmentRecommendationListResult>(`/commitments/recommendations${qs ? `?${qs}` : ''}`)
}

export async function decideCommitmentRecommendation(
  id: string,
  decision: 'approve' | 'reject' | 'defer',
  reason?: string,
): Promise<CommitmentRecommendation> {
  if (USE_MOCKS) throw new Error('Not available in mock mode')
  return request<CommitmentRecommendation>(`/commitments/recommendations/${id}/${decision}`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}