import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { auditKeys } from '@/lib/api/queryKeys'
import {
  cleanupAuditExports,
  createAuditExport,
  deleteAuditExport,
  listAuditEvents,
  listAuditExports,
} from './api'
import type { AuditExportFormat, AuditQueryParams } from './types'

export function useAuditList(q: AuditQueryParams) {
  return useQuery({ queryKey: auditKeys.list(q), queryFn: () => listAuditEvents(q) })
}

export function useAuditExports() {
  return useQuery({
    queryKey: auditKeys.exports(),
    queryFn: listAuditExports,
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? []
      const hasActive = items.some(
        (e) => e.status === 'pending' || e.status === 'running',
      )
      return hasActive ? 3000 : false
    },
  })
}

export function useCreateAuditExport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ format, query }: { format: AuditExportFormat; query: AuditQueryParams }) =>
      createAuditExport(format, query),
    onSuccess: () => qc.invalidateQueries({ queryKey: auditKeys.all }),
  })
}

export function useDeleteAuditExport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteAuditExport(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: auditKeys.all }),
  })
}

export function useCleanupAuditExports() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => cleanupAuditExports(),
    onSuccess: () => qc.invalidateQueries({ queryKey: auditKeys.all }),
  })
}