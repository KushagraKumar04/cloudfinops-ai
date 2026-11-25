import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { cloudAccountKeys } from '@/lib/api/queryKeys'
import {
  bulkDisableAccounts,
  bulkEnableAccounts,
  connectAws,
  connectAzure,
  deleteCloudAccount,
  listCloudAccounts,
  syncCloudAccount,
  validateCloudAccount,
  verifyCloudAccount,
} from './api'
import type { AwsConnectPayload, AzureConnectPayload } from './api'

export function useCloudAccounts() {
  return useQuery({ queryKey: cloudAccountKeys.list(), queryFn: listCloudAccounts })
}

export function useConnectAws() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: AwsConnectPayload) => connectAws(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: cloudAccountKeys.all }),
  })
}

export function useConnectAzure() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: AzureConnectPayload) => connectAzure(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: cloudAccountKeys.all }),
  })
}

export function useVerifyCloudAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => verifyCloudAccount(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: cloudAccountKeys.all }),
  })
}

export function useSyncCloudAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => syncCloudAccount(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: cloudAccountKeys.all }),
  })
}

export function useValidateCloudAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => validateCloudAccount(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: cloudAccountKeys.all }),
  })
}

export function useDeleteCloudAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteCloudAccount(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: cloudAccountKeys.all }),
  })
}

export function useBulkDisableAccounts() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ids: string[]) => bulkDisableAccounts(ids),
    onSuccess: () => qc.invalidateQueries({ queryKey: cloudAccountKeys.all }),
  })
}

export function useBulkEnableAccounts() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ids: string[]) => bulkEnableAccounts(ids),
    onSuccess: () => qc.invalidateQueries({ queryKey: cloudAccountKeys.all }),
  })
}