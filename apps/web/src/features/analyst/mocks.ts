import type { AnalystResponse, ToolCall } from './types'

const delay = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))

function uid(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`
}

interface RunSpec {
  plan: string[]
  toolCalls: Omit<ToolCall, 'id'>[]
  response: AnalystResponse
}

function costIncreaseRun(): RunSpec {
  return {
    plan: [
      'Identify the services with the largest absolute change vs previous period',
      'Compare against 14-day rolling baseline and pricing history',
      'Attribute the change to usage, price, or configuration',
    ],
    toolCalls: [
      {
        name: 'get_cost_summary',
        args: { range: '7d', provider: 'AWS' },
        resultSummary: 'AWS spend $32,120 · +24.5% vs prior 7d',
        durationMs: 180,
      },
      {
        name: 'get_cost_breakdown',
        args: { dimension: 'service', range: '7d' },
        resultSummary: 'Top movers: EC2 +$3,820 · EKS +$640 · RDS +$180',
        durationMs: 220,
      },
      {
        name: 'get_resource_metrics',
        args: { service: 'EC2', range: '30d' },
        resultSummary: '3 resources launched in window · 1 changed instance family',
        durationMs: 260,
      },
      {
        name: 'get_prices',
        args: { resource_type: 'm5', region: 'us-east-1' },
        resultSummary: 'No change to m5 on-demand list price in window',
        durationMs: 140,
      },
    ],
    response: {
      answer:
        'AWS compute spend rose 24.5% (+$3,820) in the last 7 days. The change is usage-driven, not price-driven: the EKS node group in us-east-1 scaled from 9 to 12 m5.2xlarge nodes on Sep 12, and one EC2 instance changed family. No m5 pricing changes were observed in the window.',
      findings: [
        {
          severity: 'critical',
          title: 'EC2 us-east-1 up $3,820',
          detail: 'Driven by node group scale-out and one instance family change.',
        },
        {
          severity: 'warning',
          title: 'EKS node group scaled +3 nodes',
          detail: 'Node group desired size grew from 9 to 12 during the period.',
        },
        {
          severity: 'info',
          title: 'No pricing change detected',
          detail: 'm5 on-demand list price in us-east-1 remained flat.',
        },
      ],
      evidence: [
        { label: 'EC2 change', value: '+$3,820 (24.5%)', source: 'Cost Explorer' },
        { label: 'EKS change', value: '+$640 (11.8%)', source: 'Cost Explorer' },
        { label: 'Node count delta', value: '+3 nodes', source: 'EKS DescribeNodegroup' },
        { label: 'Price change', value: 'none', source: 'AWS Pricing API' },
        { label: 'Metric coverage', value: '97%', source: 'FinOps engine' },
      ],
      recommendations: [
        { id: 'rec_011', title: 'Reduce EKS node group size for prod-cluster', estimatedMonthlySavings: 890, risk: 'MEDIUM' },
        { id: 'rec_001', title: 'Rightsize api-server-01 from m5.4xlarge to m5.2xlarge', estimatedMonthlySavings: 290, risk: 'MEDIUM' },
      ],
      confidence: 0.88,
      requires_human_review: true,
      followUps: [
        'Which specific pods drove the EKS scale-out?',
        'Show me the daily breakdown for EC2 in us-east-1.',
      ],
    },
  }
}

function idleResourcesRun(): RunSpec {
  return {
    plan: [
      'Enumerate resources with low utilization and sufficient metric coverage',
      'Filter out production resources and resources missing metrics',
      'Rank candidates by annualized savings',
    ],
    toolCalls: [
      {
        name: 'find_idle_resources',
        args: { threshold_cpu: 15, days: 30 },
        resultSummary: '7 candidates across AWS and Azure',
        durationMs: 320,
      },
      {
        name: 'get_resource_metrics',
        args: { window: '30d' },
        resultSummary: 'Metric coverage ≥ 90% on 6 of 7 candidates',
        durationMs: 240,
      },
      {
        name: 'calculate_savings',
        args: { candidate_count: 7 },
        resultSummary: 'Total identified savings $1,463 / mo',
        durationMs: 120,
      },
    ],
    response: {
      answer:
        'I found 7 resources with sustained low utilization and sufficient metric coverage. Three are unattached storage or unused network resources (safest to remove), two are non-production compute candidates, and two are production candidates requiring maintenance windows. Combined identified savings are $1,463/month.',
      findings: [
        { severity: 'warning', title: '3 unattached storage/network resources', detail: 'No I/O or association in 30+ days. Low risk to remove.' },
        { severity: 'warning', title: '2 non-production compute candidates', detail: 'Off-hours utilization below 5%. Scheduling or rightsizing is viable.' },
        { severity: 'info', title: '2 production candidates require review', detail: 'Production compute with low steady-state utilization.' },
      ],
      evidence: [
        { label: 'Candidates', value: '7', source: 'FinOps engine' },
        { label: 'Total identified savings', value: '$1,463 / mo', source: 'Savings calculator' },
        { label: 'Metric coverage', value: '≥ 90% on 6/7', source: 'CloudWatch · Azure Monitor' },
      ],
      recommendations: [
        { id: 'rec_002', title: 'Delete unattached EBS volume orphan-volume-500gb', estimatedMonthlySavings: 60, risk: 'LOW' },
        { id: 'rec_003', title: 'Release unused Elastic IP unused-eip-1', estimatedMonthlySavings: 3.6, risk: 'LOW' },
        { id: 'rec_010', title: 'Delete unattached EBS staging-scratch-200gb', estimatedMonthlySavings: 20, risk: 'LOW' },
        { id: 'rec_006', title: 'Stop idle staging-worker-01 outside business hours', estimatedMonthlySavings: 18, risk: 'MEDIUM' },
      ],
      confidence: 0.91,
      requires_human_review: true,
    },
  }
}

function topSavingsRun(): RunSpec {
  return {
    plan: [
      'Enumerate all open recommendations sorted by estimated monthly savings',
      'Exclude BLOCKED recommendations from the safe-to-act list',
      'Group by effort and risk',
    ],
    toolCalls: [
      {
        name: 'list_recommendations',
        args: { status: 'pending', sort: 'estimated_monthly_savings:desc' },
        resultSummary: '9 pending · total $2,438 / mo',
        durationMs: 210,
      },
      {
        name: 'check_policy',
        args: { recommendation_ids: 'all' },
        resultSummary: '1 blocked · 3 require approval · 5 safe-to-approve',
        durationMs: 190,
      },
    ],
    response: {
      answer:
        'The top savings opportunities are concentrated in two areas: an EKS node group reduction ($890/mo) and S3 Intelligent-Tiering on the logs bucket ($420/mo). Together they account for 54% of identified pending savings. One recommendation (Azure SQL tier change) is BLOCKED by policy.',
      findings: [
        { severity: 'info', title: 'EKS node group reduction', detail: '$890 / mo · MEDIUM risk · already approved.' },
        { severity: 'info', title: 'S3 Intelligent-Tiering', detail: '$420 / mo · LOW risk · pending approval.' },
        { severity: 'warning', title: 'Azure SQL tier change blocked', detail: 'Requires data governance approval before it can proceed.' },
      ],
      evidence: [
        { label: 'Pending recommendations', value: '9', source: 'FinOps engine' },
        { label: 'Pending savings', value: '$2,438 / mo', source: 'Savings calculator' },
        { label: 'Policy-blocked', value: '1', source: 'Policy engine' },
      ],
      recommendations: [
        { id: 'rec_011', title: 'Reduce EKS node group size for prod-cluster', estimatedMonthlySavings: 890, risk: 'MEDIUM' },
        { id: 'rec_005', title: 'Enable S3 Intelligent-Tiering on acme-logs-prod', estimatedMonthlySavings: 420, risk: 'LOW' },
        { id: 'rec_001', title: 'Rightsize api-server-01 from m5.4xlarge to m5.2xlarge', estimatedMonthlySavings: 290, risk: 'MEDIUM' },
      ],
      confidence: 0.9,
      requires_human_review: false,
    },
  }
}

function forecastRun(): RunSpec {
  return {
    plan: [
      'Retrieve daily historical spend for the trailing 90 days',
      'Fit a trend plus weekday-seasonal model',
      'Produce month-end and 30-day projections with a confidence interval',
    ],
    toolCalls: [
      {
        name: 'get_cost_trend',
        args: { range: '90d' },
        resultSummary: '90 daily points · 2 providers',
        durationMs: 260,
      },
      {
        name: 'forecast_spend',
        args: { horizon: '30d', model: 'trend+seasonal' },
        resultSummary: 'Projected 30-day $214,500 (±$6,800)',
        durationMs: 340,
      },
    ],
    response: {
      answer:
        'Based on the trailing 90 days, the current month-end projection is $214,500 (budget $220,000). The 30-day forward estimate is $215,900 with an 80% confidence interval of $209,100 to $222,700. The upward trend is driven by EC2 and Azure VMs.',
      findings: [
        { severity: 'info', title: 'Month-end projection', detail: '$214,500 — 98% of the $220,000 budget.' },
        { severity: 'warning', title: 'Budget breach risk', detail: 'Under the upper bound of the interval, spend could exceed the budget.' },
      ],
      evidence: [
        { label: 'Historical points', value: '90 days', source: 'Cost records' },
        { label: 'Projected month-end', value: '$214,500', source: 'Forecast model' },
        { label: '80% CI (30d)', value: '$209,100 – $222,700', source: 'Forecast model' },
      ],
      recommendations: [],
      confidence: 0.82,
      requires_human_review: false,
    },
  }
}

function storageRun(): RunSpec {
  return {
    plan: [
      'Aggregate storage cost by service and account',
      'Identify buckets and volumes with tiering or lifecycle opportunities',
      'Estimate savings from tier transitions',
    ],
    toolCalls: [
      {
        name: 'get_cost_breakdown',
        args: { dimension: 'service', filter: 'storage' },
        resultSummary: 'S3 $12.6k · EBS $8.9k · Blob $7.8k · Azure Disk $2.4k',
        durationMs: 220,
      },
      {
        name: 'find_rightsizing_candidates',
        args: { type: 'storage' },
        resultSummary: '5 candidates · $603 / mo',
        durationMs: 280,
      },
    ],
    response: {
      answer:
        'Storage spend this month is $31,700 across AWS and Azure. The single largest opportunity is enabling S3 Intelligent-Tiering on acme-logs-prod ($420/mo). Two unattached EBS volumes contribute $80/mo and can be removed after a snapshot check.',
      findings: [
        { severity: 'warning', title: 'S3 cold data tiering', detail: '48 TB in acme-logs-prod · 63% not accessed in 90 days.' },
        { severity: 'info', title: 'Two unattached EBS volumes', detail: '$80 / mo combined. Attach or delete.' },
      ],
      evidence: [
        { label: 'S3 storage size', value: '48,000 GB', source: 'S3 Inventory' },
        { label: 'Unattached volumes', value: '2', source: 'EC2 DescribeVolumes' },
        { label: 'Storage spend MTD', value: '$31,700', source: 'Cost Explorer' },
      ],
      recommendations: [
        { id: 'rec_005', title: 'Enable S3 Intelligent-Tiering on acme-logs-prod', estimatedMonthlySavings: 420, risk: 'LOW' },
        { id: 'rec_002', title: 'Delete unattached EBS volume orphan-volume-500gb', estimatedMonthlySavings: 60, risk: 'LOW' },
        { id: 'rec_010', title: 'Delete unattached EBS staging-scratch-200gb', estimatedMonthlySavings: 20, risk: 'LOW' },
      ],
      confidence: 0.87,
      requires_human_review: false,
    },
  }
}

function genericRun(question: string): RunSpec {
  return {
    plan: [
      'Clarify the intent of the question',
      'Retrieve the minimum context needed to answer',
      'Return a structured response',
    ],
    toolCalls: [
      {
        name: 'get_cost_summary',
        args: { range: '30d' },
        resultSummary: '$184,320 MTD across AWS and Azure',
        durationMs: 180,
      },
    ],
    response: {
      answer: `I can investigate cost changes, idle resources, top savings, forecasts, and storage. For "${question.trim()}", try one of the suggested questions or rephrase with a time range and provider.`,
      findings: [],
      evidence: [
        { label: 'Current MTD spend', value: '$184,320', source: 'Cost records' },
        { label: 'Providers connected', value: 'AWS, Azure', source: 'Cloud connectors' },
      ],
      recommendations: [],
      confidence: 0.55,
      requires_human_review: false,
      followUps: [
        'Why did compute cost increase this week?',
        'Show me our top 10 savings opportunities.',
        'Which resources are idle?',
      ],
    },
  }
}

function pickRun(question: string): RunSpec {
  const q = question.toLowerCase()
  if (/(why|increase|rise|spike|jump).*(cost|spend|compute|bill)/.test(q) || /cost.*increas/.test(q)) return costIncreaseRun()
  if (/(idle|underutil|unused|unattached)/.test(q)) return idleResourcesRun()
  if (/(top|savings|opportunit|optimize)/.test(q)) return topSavingsRun()
  if (/(forecast|project|next month)/.test(q)) return forecastRun()
  if (/(storage|s3|blob|bucket|disk|volume)/.test(q)) return storageRun()
  return genericRun(question)
}

export interface AnalystRunUpdate {
  plan?: string[]
  toolCall?: ToolCall
  response?: AnalystResponse
  status: 'planning' | 'running' | 'complete'
}

export async function simulateAnalystRun(
  question: string,
  onUpdate: (update: AnalystRunUpdate) => void,
): Promise<void> {
  const spec = pickRun(question)
  onUpdate({ status: 'planning' })
  await delay(320)
  onUpdate({ status: 'running', plan: spec.plan })
  for (const call of spec.toolCalls) {
    await delay(220)
    onUpdate({ status: 'running', toolCall: { ...call, id: uid('tool') } })
  }
  await delay(260)
  onUpdate({ status: 'complete', response: spec.response })
}

export const SUGGESTED_QUESTIONS = [
  'Why did compute cost increase this week?',
  'Which resources are idle or underutilized?',
  'Show me our top savings opportunities.',
  'Forecast spend for the next 30 days.',
  'Why is storage cost increasing?',
]