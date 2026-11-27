import type {
  CommitmentListResult,
  CommitmentRecommendationListResult,
  CoverageSummary,
} from './types'

export const MOCK_COVERAGE_SUMMARY: CoverageSummary = {
  totalMonthlySpend: 0,
  eligibleMonthlySpend: 0,
  coveredMonthlySpend: 0,
  uncoveredMonthlySpend: 0,
  coveragePct: 0,
  activeCommitments: 0,
  expiringWithin60Days: 0,
  averageUtilizationPct: 0,
  realizedMonthlySavings: 0,
  potentialMonthlySavings: 0,
  onDemandRiskPct: 0,
}

export const MOCK_COMMITMENTS: CommitmentListResult = { items: [], total: 0 }

export const MOCK_RECOMMENDATIONS: CommitmentRecommendationListResult = {
  items: [],
  total: 0,
  totals: { pending: 0, approved: 0, rejected: 0, deferred: 0, pending_savings: 0, approved_savings: 0 },
}