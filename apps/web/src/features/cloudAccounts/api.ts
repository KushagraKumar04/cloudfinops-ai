import { request, USE_MOCKS, withMockDelay } from '@/lib/api/client'
import { MOCK_CLOUD_ACCOUNTS } from './mocks'
import type { CloudAccount } from './types'

export interface AwsConnectPayload {
  name: string
  accountIdentifier: string
  roleArn: string
  environment: string
  regions: string[]
  externalId?: string
}

export interface AwsConnectResult {
  id: string
  externalId: string
  roleArn: string
  cloudformationUrl: string
  trustPolicy: unknown
  note: string
}

export interface AzureConnectPayload {
  name: string
  subscriptionId: string
  tenantId: string
  clientId: string
  clientSecret: string
  environment: string
}

export interface AzureConnectResult {
  id: string
  subscriptionId: string
  azCliCommand: string
  note: string
}

export interface VerifyResult {
  ok: boolean
  message: string
  accountId: string | null
}

export interface SetupPreview {
  provider: string
  externalId?: string
  roleName?: string
  trustPolicy?: unknown
  managedPolicies?: string[]
  subscriptionId?: string
  clientId?: string
  tenantId?: string
  azCommand?: string
}

export async function listCloudAccounts(): Promise<CloudAccount[]> {
  if (USE_MOCKS) return withMockDelay(MOCK_CLOUD_ACCOUNTS)
  return request<CloudAccount[]>('/cloud/accounts')
}

export async function connectAws(payload: AwsConnectPayload): Promise<AwsConnectResult> {
  if (USE_MOCKS) {
    return withMockDelay({
      id: `acc_aws_${Math.random().toString(36).slice(2, 8)}`,
      externalId: `cloudfinops-demo-${Math.random().toString(36).slice(2, 10)}`,
      roleArn: payload.roleArn,
      cloudformationUrl: 'https://console.aws.amazon.com/cloudformation/home',
      trustPolicy: {
        Version: '2012-10-17',
        Statement: [
          {
            Effect: 'Allow',
            Principal: { AWS: 'arn:aws:iam::000000000000:root' },
            Action: 'sts:AssumeRole',
            Condition: { StringEquals: { 'sts:ExternalId': 'demo-external-id' } },
          },
        ],
      },
      note: 'Mock mode. Real mode returns a live external ID and trust policy.',
    })
  }
  return request<AwsConnectResult>('/cloud/accounts/aws', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function connectAzure(payload: AzureConnectPayload): Promise<AzureConnectResult> {
  if (USE_MOCKS) {
    return withMockDelay({
      id: `acc_az_${Math.random().toString(36).slice(2, 8)}`,
      subscriptionId: payload.subscriptionId,
      azCliCommand: `az role assignment create --assignee "${payload.clientId}" --role "Cost Management Reader" --scope /subscriptions/${payload.subscriptionId}`,
      note: 'Mock mode.',
    })
  }
  return request<AzureConnectResult>('/cloud/accounts/azure', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function verifyCloudAccount(id: string): Promise<VerifyResult> {
  if (USE_MOCKS) return withMockDelay({ ok: true, message: 'Mock verification succeeded', accountId: id })
  return request<VerifyResult>(`/cloud/accounts/${id}/verify`, { method: 'POST' })
}

export async function syncCloudAccount(id: string): Promise<{ id: string; status: 'started' }> {
  if (USE_MOCKS) return withMockDelay({ id, status: 'started' })
  return request<{ id: string; status: 'started' }>(`/cloud/accounts/${id}/sync`, { method: 'POST' })
}

export async function validateCloudAccount(id: string): Promise<{ id: string; ok: boolean; message: string }> {
  if (USE_MOCKS) return withMockDelay({ id, ok: true, message: 'Connection validated' })
  return request<{ id: string; ok: boolean; message: string }>(`/cloud/accounts/${id}/validate`, { method: 'POST' })
}

export async function deleteCloudAccount(id: string): Promise<void> {
  if (USE_MOCKS) return withMockDelay(undefined)
  await request<void>(`/cloud/accounts/${id}`, { method: 'DELETE' })
}

export interface BulkActionResult {
  succeeded: string[]
  failed: { id: string; error: string }[]
  total: number
  succeededCount: number
  failedCount: number
}

export async function bulkDisableAccounts(ids: string[]): Promise<BulkActionResult> {
  if (USE_MOCKS) throw new Error('Not available in mock mode')
  return request<BulkActionResult>('/cloud/accounts/bulk-disable', {
    method: 'POST',
    body: JSON.stringify({ ids }),
  })
}

export async function bulkEnableAccounts(ids: string[]): Promise<BulkActionResult> {
  if (USE_MOCKS) throw new Error('Not available in mock mode')
  return request<BulkActionResult>('/cloud/accounts/bulk-enable', {
    method: 'POST',
    body: JSON.stringify({ ids }),
  })
}

export async function getSetupPreview(id: string): Promise<SetupPreview> {
  if (USE_MOCKS) {
    return withMockDelay({
      provider: 'AWS',
      externalId: 'mock-external-id',
      roleName: 'CloudFinOpsReadOnly',
      trustPolicy: {},
      managedPolicies: [],
    })
  }
  return request<SetupPreview>(`/cloud/accounts/${id}/setup-preview`)
}