import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminKeys } from '@/lib/api/queryKeys'
import {
  getPlatformStats,
  getTenant,
  listTenants,
  listUsers,
  updateUser,
} from './api'

export function usePlatformStats() {
  return useQuery({ queryKey: adminKeys.stats(), queryFn: getPlatformStats })
}

export function useTenants() {
  return useQuery({ queryKey: adminKeys.tenants(), queryFn: listTenants })
}

export function useTenant(id: string | undefined) {
  return useQuery({
    queryKey: adminKeys.tenant(id ?? ''),
    queryFn: () => getTenant(id as string),
    enabled: Boolean(id),
  })
}

export function useAdminUsers() {
  return useQuery({ queryKey: adminKeys.users(), queryFn: listUsers })
}

export function useUpdateAdminUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string
      payload: { isActive?: boolean; isSuperuser?: boolean }
    }) => updateUser(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: adminKeys.all }),
  })
}