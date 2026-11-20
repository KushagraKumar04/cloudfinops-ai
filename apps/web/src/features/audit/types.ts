export type AuditCategory =
  | 'cloud.account'
  | 'billing.sync'
  | 'resource'
  | 'cost.anomaly'
  | 'recommendation'
  | 'execution'
  | 'policy'
  | 'auth'

export type AuditSeverity = 'info' | 'warning' | 'critical'

export interface AuditEvent {
  id: string
  at: string
  category: AuditCategory
  severity: AuditSeverity
  actor: string
  action: string
  subject: string
  details: string
  metadata: { key: string; value: string }[]
}

export interface AuditQueryParams {
  search: string
  category: AuditCategory | 'all'
  severity: AuditSeverity | 'all'
  page: number
  pageSize: number
}

export interface AuditListResult {
  items: AuditEvent[]
  total: number
  page: number
  pageSize: number
}

export type AuditExportFormat = 'csv' | 'json'
export type AuditExportStatus = 'pending' | 'running' | 'completed' | 'failed'
export type AuditExportBackend = 'local' | 's3' | 'azure'

export interface AuditExport {
  id: string
  format: AuditExportFormat
  storageBackend: AuditExportBackend
  sizeBytes: number
  recordCount: number
  filters: Record<string, unknown>
  status: AuditExportStatus
  error: string | null
  createdAt: string
  completedAt: string | null
  expiresAt: string
  deletedAt: string | null
  downloadUrl: string | null
}

export interface AuditExportListResult {
  items: AuditExport[]
  total: number
}