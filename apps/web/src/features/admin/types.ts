export interface TenantSummary {
  id: string
  slug: string
  name: string
  createdAt: string
  userCount: number
  cloudAccountCount: number
  resourceCount: number
  recommendationCount: number
  costRecordCount: number
  auditEventCount: number
}

export interface AdminMember {
  userId: string
  email: string
  fullName: string
  role: 'owner' | 'admin' | 'member' | 'viewer'
  isActive: boolean
  isSuperuser: boolean
  joinedAt: string
}

export interface AdminCloudAccount {
  id: string
  name: string
  provider: 'AWS' | 'Azure'
  environment: string
  status: string
  resourceCount: number
  monthlySpend: number
  disabled: boolean
}

export interface TenantDetail extends TenantSummary {
  members: AdminMember[]
  cloudAccounts: AdminCloudAccount[]
  recentRecommendations: number
}

export interface AdminUserRow {
  id: string
  email: string
  fullName: string
  isActive: boolean
  isSuperuser: boolean
  createdAt: string
  tenantCount: number
}

export interface TenantListResult {
  items: TenantSummary[]
  total: number
}

export interface UserListResult {
  items: AdminUserRow[]
  total: number
}

export interface PlatformStats {
  tenantCount: number
  userCount: number
  activeUserCount: number
  cloudAccountCount: number
  resourceCount: number
  recommendationCount: number
  costRecordCount: number
  auditEventCount: number
  totalMonthlySpend: number
  breakdown: { accounts_by_provider?: Record<string, number> }
}