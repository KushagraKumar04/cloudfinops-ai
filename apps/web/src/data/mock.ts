export const DEMO = true

export const accounts = [
  { id: 'acc_aws_prod', provider: 'AWS', name: 'Production', identifier: '123456789012', environment: 'production' },
  { id: 'acc_aws_stg', provider: 'AWS', name: 'Staging', identifier: '210987654321', environment: 'staging' },
  { id: 'acc_az_prod', provider: 'Azure', name: 'Production', identifier: 'sub-9f2c-1a4e', environment: 'production' },
]

export const kpis = {
  currentMonthSpend: 184320,
  previousMonthSpend: 156210,
  momChangePct: 18.0,
  projectedMonthEnd: 214500,
  budget: 220000,
  identifiedWaste: 27480,
  estimatedSavings: 21360,
  realizedSavings: 8420,
  anomalyCount: 7,
  highRiskRecommendations: 3,
}

export const spendTrend = [
  { date: '2026-09-01', aws: 4120, azure: 1980 },
  { date: '2026-09-02', aws: 4260, azure: 2010 },
  { date: '2026-09-03', aws: 4180, azure: 1990 },
  { date: '2026-09-04', aws: 4520, azure: 2120 },
  { date: '2026-09-05', aws: 4380, azure: 2080 },
  { date: '2026-09-06', aws: 4210, azure: 2040 },
  { date: '2026-09-07', aws: 4090, azure: 1980 },
  { date: '2026-09-08', aws: 4470, azure: 2110 },
  { date: '2026-09-09', aws: 4620, azure: 2180 },
  { date: '2026-09-10', aws: 4780, azure: 2230 },
  { date: '2026-09-11', aws: 4910, azure: 2280 },
  { date: '2026-09-12', aws: 4820, azure: 2240 },
  { date: '2026-09-13', aws: 4680, azure: 2190 },
  { date: '2026-09-14', aws: 4890, azure: 2300 },
]

export const costByProvider = [
  { name: 'AWS', value: 128400 },
  { name: 'Azure', value: 55920 },
]

export const costByService = [
  { name: 'EC2', value: 64200 },
  { name: 'RDS', value: 21800 },
  { name: 'S3', value: 12600 },
  { name: 'EKS', value: 11200 },
  { name: 'CloudWatch', value: 4100 },
  { name: 'Data Transfer', value: 8900 },
  { name: 'Azure VMs', value: 28400 },
  { name: 'Azure SQL', value: 14200 },
  { name: 'Blob Storage', value: 7800 },
  { name: 'Other', value: 9720 },
]

export const recommendations = [
  {
    id: 'rec_001',
    title: 'Rightsize EC2 m5.4xlarge to m5.2xlarge',
    resource: 'i-0a1b2c3d4e5f67890',
    type: 'compute.rightsizing',
    risk: 'MEDIUM' as const,
    confidence: 0.92,
    estimatedMonthlySavings: 290,
    status: 'pending' as const,
    createdAt: '2026-09-22T10:14:00Z',
  },
  {
    id: 'rec_002',
    title: 'Delete unattached EBS volume gp3 500GB',
    resource: 'vol-0f1e2d3c4b5a69788',
    type: 'storage.unattached',
    risk: 'LOW' as const,
    confidence: 0.99,
    estimatedMonthlySavings: 60,
    status: 'pending' as const,
    createdAt: '2026-09-22T09:02:00Z',
  },
  {
    id: 'rec_003',
    title: 'Release unused Elastic IP',
    resource: 'eipalloc-0a9b8c7d6e5f4a3b2',
    type: 'network.unused_eip',
    risk: 'LOW' as const,
    confidence: 0.98,
    estimatedMonthlySavings: 3.6,
    status: 'approved' as const,
    createdAt: '2026-09-21T17:45:00Z',
  },
  {
    id: 'rec_004',
    title: 'Downsize Azure VM Standard_D8s_v5 to Standard_D4s_v5',
    resource: '/subscriptions/sub-9f2c/resourceGroups/rg-prod/providers/Microsoft.Compute/virtualMachines/vm-app-02',
    type: 'compute.rightsizing',
    risk: 'HIGH' as const,
    confidence: 0.78,
    estimatedMonthlySavings: 340,
    status: 'pending' as const,
    createdAt: '2026-09-21T14:20:00Z',
  },
  {
    id: 'rec_005',
    title: 'Enable S3 Intelligent-Tiering on logs bucket',
    resource: 'arn:aws:s3:::acme-logs-prod',
    type: 'storage.tiering',
    risk: 'LOW' as const,
    confidence: 0.88,
    estimatedMonthlySavings: 420,
    status: 'pending' as const,
    createdAt: '2026-09-20T11:11:00Z',
  },
]

export const anomalies = [
  {
    id: 'anom_001',
    service: 'EC2',
    account: 'Production',
    detectedAt: '2026-09-14T08:00:00Z',
    deltaPct: 42,
    deltaAmount: 3820,
    description: 'Compute spend on us-east-1 increased 42% vs 14-day baseline.',
    severity: 'high' as const,
  },
  {
    id: 'anom_002',
    service: 'Data Transfer',
    account: 'Production',
    detectedAt: '2026-09-12T08:00:00Z',
    deltaPct: 28,
    deltaAmount: 640,
    description: 'Cross-region data transfer increased 28% week over week.',
    severity: 'medium' as const,
  },
  {
    id: 'anom_003',
    service: 'Azure SQL',
    account: 'Production',
    detectedAt: '2026-09-10T08:00:00Z',
    deltaPct: 19,
    deltaAmount: 410,
    description: 'Azure SQL compute tier utilization above expected range.',
    severity: 'medium' as const,
  },
]