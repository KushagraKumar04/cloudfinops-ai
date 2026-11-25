export type CommitmentType =
  | 'reserved_instance'
  | 'savings_plan'
  | 'reserved_vm'
  | 'reserved_capacity'

export type PaymentOption =
  | 'all_upfront'
  | 'partial_upfront'
  | 'no_upfront'
  | 'monthly'

export type CommitmentStatus = 'active' | 'expired' | 'pending' | 'cancelled'
export type RecommendationStatus = 'pending' | 'approved' | 'rejected' | 'deferred'
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'BLOCKED'

export interface Commitment {
  id: string
  cloudAccountId: string
  accountName: string
  provider: 'AWS' | 'Azure'
  commitmentType: CommitmentType
  service: string
  region: string
  termMonths: number
  paymentOption: PaymentOption
  monthlyCost: number
  monthlySavings: number
  hourlyCommitment: number | null
  instanceCount: number | null
  startDate: string
  endDate: string
  status: CommitmentStatus
  utilizationPct: number
  currency: string
}

export interface CoverageSummary {
  totalMonthlySpend: number
  eligibleMonthlySpend: number
  coveredMonthlySpend: number
  uncoveredMonthlySpend: number
  coveragePct: number
  activeCommitments: number
  expiringWithin60Days: number
  averageUtilizationPct: number
  realizedMonthlySavings: number
  potentialMonthlySavings: number
  onDemandRiskPct: number
}

export interface CommitmentApproval {
  id: string
  approver: string
  decision: string
  reason: string | null
  createdAt: string
}

export interface CommitmentRecommendation {
  id: string
  cloudAccountId: string
  accountName: string
  provider: 'AWS' | 'Azure'
  commitmentType: CommitmentType
  service: string
  region: string
  title: string
  summary: string
  rationale: string
  termMonths: number
  paymentOption: PaymentOption
  recommendedHourlyCommitment: number | null
  recommendedInstanceCount: number | null
  estimatedMonthlyCost: number
  estimatedMonthlySavings: number
  estimatedAnnualSavings: number
  coverageBeforePct: number
  coverageAfterPct: number
  breakEvenMonths: number
  risk: RiskLevel
  riskReasons: string[]
  confidence: number
  status: RecommendationStatus
  evidence: { label: string; value: string; source: string }[]
  impact: { financial: string; operational: string; risk: string }
  currency: string
  createdAt: string
  updatedAt: string
  history: CommitmentApproval[]
}

export interface CommitmentListResult {
  items: Commitment[]
  total: number
}

export interface CommitmentRecommendationListResult {
  items: CommitmentRecommendation[]
  total: number
  totals: Record<string, number>
}