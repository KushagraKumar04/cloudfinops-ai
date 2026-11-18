import type { AuditEvent, AuditListResult, AuditQueryParams } from './types'

function iso(dayOffset: number, hour: number, minute: number): string {
  const d = new Date()
  d.setDate(d.getDate() - dayOffset)
  d.setHours(hour, minute, 0, 0)
  return d.toISOString()
}

const EVENTS: AuditEvent[] = [
  {
    id: 'aud_0001',
    at: iso(0, 9, 12),
    category: 'recommendation',
    severity: 'info',
    actor: 'demo.user@acme.io',
    action: 'Approved recommendation',
    subject: 'rec_003 · Release unused Elastic IP unused-eip-1',
    details: 'Approved via Approvals queue.',
    metadata: [
      { key: 'recommendation_id', value: 'rec_003' },
      { key: 'decision', value: 'approve' },
    ],
  },
  {
    id: 'aud_0002',
    at: iso(0, 8, 4),
    category: 'billing.sync',
    severity: 'info',
    actor: 'ingestion-worker',
    action: 'Billing sync completed',
    subject: 'AWS Production · 2026-09-22',
    details: 'Records fetched 42118, inserted 42118, dedup 0.',
    metadata: [
      { key: 'provider', value: 'AWS' },
      { key: 'account', value: '123456789012' },
      { key: 'duration_ms', value: '8420' },
    ],
  },
  {
    id: 'aud_0003',
    at: iso(1, 17, 45),
    category: 'recommendation',
    severity: 'info',
    actor: 'finops-engine',
    action: 'Recommendation created',
    subject: 'rec_001 · Rightsize api-server-01',
    details: 'Rule: compute.rightsizing · avg_cpu_30d=12% · threshold=15%.',
    metadata: [
      { key: 'recommendation_id', value: 'rec_001' },
      { key: 'rule', value: 'compute.rightsizing' },
      { key: 'estimated_monthly_savings', value: '290' },
    ],
  },
  {
    id: 'aud_0004',
    at: iso(1, 15, 30),
    category: 'cost.anomaly',
    severity: 'warning',
    actor: 'finops-engine',
    action: 'Anomaly detected',
    subject: 'EC2 · us-east-1',
    details: 'Spend +42% vs 14-day baseline.',
    metadata: [
      { key: 'provider', value: 'AWS' },
      { key: 'service', value: 'EC2' },
      { key: 'delta_amount', value: '3820' },
    ],
  },
  {
    id: 'aud_0005',
    at: iso(2, 11, 10),
    category: 'cloud.account',
    severity: 'info',
    actor: 'admin@acme.io',
    action: 'Cloud account connected',
    subject: 'Azure Production · sub-9f2c-1a4e',
    details: 'Read-only connector established. Resource Graph + Cost Management enabled.',
    metadata: [
      { key: 'provider', value: 'Azure' },
      { key: 'mode', value: 'read-only' },
    ],
  },
  {
    id: 'aud_0006',
    at: iso(2, 9, 0),
    category: 'policy',
    severity: 'warning',
    actor: 'policy-engine',
    action: 'Recommendation blocked',
    subject: 'rec_008 · Azure SQL tier change',
    details: 'Policy: database.require_approval=true. Requires data governance sign-off.',
    metadata: [
      { key: 'recommendation_id', value: 'rec_008' },
      { key: 'policy', value: 'database.require_approval' },
    ],
  },
  {
    id: 'aud_0007',
    at: iso(3, 16, 20),
    category: 'recommendation',
    severity: 'info',
    actor: 'mike@acme.io',
    action: 'Deferred recommendation',
    subject: 'rec_009 · Dev-hours schedule for vm-dev-01',
    details: 'Reason: Align rollout with next sprint.',
    metadata: [
      { key: 'recommendation_id', value: 'rec_009' },
      { key: 'decision', value: 'defer' },
    ],
  },
  {
    id: 'aud_0008',
    at: iso(4, 10, 4),
    category: 'execution',
    severity: 'info',
    actor: 'execution-service',
    action: 'Execution dry-run completed',
    subject: 'rec_003 · Release Elastic IP',
    details: 'Precondition check passed. No mutations applied.',
    metadata: [
      { key: 'recommendation_id', value: 'rec_003' },
      { key: 'idempotency_key', value: 'execution:rec_003:release_eip' },
    ],
  },
  {
    id: 'aud_0009',
    at: iso(5, 14, 45),
    category: 'resource',
    severity: 'info',
    actor: 'ingestion-worker',
    action: 'Resource discovered',
    subject: 'res_020 · Azure SQL S3 sql-prod-01',
    details: 'New resource observed during inventory sync.',
    metadata: [
      { key: 'provider', value: 'Azure' },
      { key: 'resource_type', value: 'Azure SQL' },
    ],
  },
  {
    id: 'aud_0010',
    at: iso(6, 9, 12),
    category: 'auth',
    severity: 'critical',
    actor: 'unknown',
    action: 'Failed login',
    subject: 'admin@acme.io',
    details: 'Five consecutive failed attempts within two minutes from an unrecognized network.',
    metadata: [
      { key: 'result', value: 'blocked' },
      { key: 'window', value: '120s' },
    ],
  },
  {
    id: 'aud_0011',
    at: iso(7, 10, 0),
    category: 'execution',
    severity: 'info',
    actor: 'sre-lead@acme.io',
    action: 'Approved recommendation',
    subject: 'rec_011 · Reduce EKS node group size',
    details: 'Approved after capacity review.',
    metadata: [
      { key: 'recommendation_id', value: 'rec_011' },
      { key: 'decision', value: 'approve' },
    ],
  },
  {
    id: 'aud_0012',
    at: iso(8, 11, 30),
    category: 'recommendation',
    severity: 'info',
    actor: 'finops-engine',
    action: 'Recommendation created',
    subject: 'rec_010 · Delete unattached EBS staging-scratch-200gb',
    details: 'Rule: storage.unattached · unattached 400d · no I/O in 30d.',
    metadata: [
      { key: 'recommendation_id', value: 'rec_010' },
      { key: 'rule', value: 'storage.unattached' },
    ],
  },
  {
    id: 'aud_0013',
    at: iso(9, 8, 15),
    category: 'billing.sync',
    severity: 'warning',
    actor: 'ingestion-worker',
    action: 'Billing sync partial',
    subject: 'Azure Production · 2026-09-13',
    details: 'Cost Management API returned partial data. Retry scheduled.',
    metadata: [
      { key: 'provider', value: 'Azure' },
      { key: 'records_fetched', value: '1842' },
      { key: 'status', value: 'DATA_PARTIAL' },
    ],
  },
  {
    id: 'aud_0014',
    at: iso(10, 15, 30),
    category: 'recommendation',
    severity: 'info',
    actor: 'finops-engine',
    action: 'Recommendation created',
    subject: 'rec_012 · Investigate legacy-batch-01 stopped instance',
    details: 'Rule: compute.idle · instance stopped 820d.',
    metadata: [
      { key: 'recommendation_id', value: 'rec_012' },
      { key: 'rule', value: 'compute.idle' },
    ],
  },
]

export function mockAuditList(q: AuditQueryParams): AuditListResult {
  let rows = [...EVENTS]
  if (q.search.trim()) {
    const term = q.search.trim().toLowerCase()
    rows = rows.filter(
      (e) =>
        e.action.toLowerCase().includes(term) ||
        e.subject.toLowerCase().includes(term) ||
        e.actor.toLowerCase().includes(term) ||
        e.details.toLowerCase().includes(term),
    )
  }
  if (q.category !== 'all') rows = rows.filter((e) => e.category === q.category)
  if (q.severity !== 'all') rows = rows.filter((e) => e.severity === q.severity)

  const total = rows.length
  const start = (q.page - 1) * q.pageSize
  const items = rows.slice(start, start + q.pageSize)
  return { items, total, page: q.page, pageSize: q.pageSize }
}