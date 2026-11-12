import { request, USE_MOCKS } from '@/lib/api/client'
import type {
  AdminUserRow,
  PlatformStats,
  TenantDetail,
  TenantListResult,
  UserListResult,
} from './types'

export async function getPlatformStats(): Promise<PlatformStats> {
  if (USE_MOCKS) throw new Error('Admin not available in mock mode')
  return request<PlatformStats>('/admin/stats')
}

export async function listTenants(): Promise<TenantListResult> {
  if (USE_MOCKS) throw new Error('Admin not available in mock mode')
  return request<TenantListResult>('/admin/tenants')
}

export async function getTenant(id: string): Promise<TenantDetail> {
  if (USE_MOCKS) throw new Error('Admin not available in mock mode')
  return request<TenantDetail>(`/admin/tenants/${id}`)
}

export async function listUsers(): Promise<UserListResult> {
  if (USE_MOCKS) throw new Error('Admin not available in mock mode')
  return request<UserListResult>('/admin/users')
}

export async function updateUser(
  id: string,
  payload: { isActive?: boolean; isSuperuser?: boolean },
): Promise<AdminUserRow> {
  if (USE_MOCKS) throw new Error('Admin not available in mock mode')
  return request<AdminUserRow>(`/admin/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}