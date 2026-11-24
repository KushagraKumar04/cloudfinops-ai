import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { commitmentKeys } from '@/lib/api/queryKeys'
import {
  decideCommitmentRecommendation,
  getCoverageSummary,
  listCommitmentRecommendations,
  listCommitments,
} from './api'

export function useCoverageSummary(provider?: string) {
  return useQuery({
    queryKey: commitmentKeys.summary(provider ?? 'all'),
    queryFn: () => getCoverageSummary(provider),
  })
}

export function useCommitments(provider?: string) {
  return useQuery({
    queryKey: commitmentKeys.list(provider ?? 'all'),
    queryFn: () => listCommitments(provider),
  })
}

export function useCommitmentRecommendations(status = 'pending', provider?: string) {
  return useQuery({
    queryKey: commitmentKeys.recommendations(status, provider ?? 'all'),
    queryFn: () => listCommitmentRecommendations(status, provider),
  })
}

export function useDecideCommitmentRecommendation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      decision,
      reason,
    }: {
      id: string
      decision: 'approve' | 'reject' | 'defer'
      reason?: string
    }) => decideCommitmentRecommendation(id, decision, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: commitmentKeys.all }),
  })
}