import { Download, Loader2, Trash2, Upload } from 'lucide-react'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { formatDateTime } from '@/lib/format'
import {
  useAuditExports,
  useCleanupAuditExports,
  useCreateAuditExport,
  useDeleteAuditExport,
} from './hooks'
import type { AuditExportFormat, AuditExportStatus, AuditQueryParams } from './types'

const STATUS_TONE: Record<AuditExportStatus, 'success' | 'warning' | 'danger' | 'neutral'> = {
  pending: 'neutral',
  running: 'warning',
  completed: 'success',
  failed: 'danger',
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function ExportPanel({ query }: { query: AuditQueryParams }) {
  const exports = useAuditExports()
  const create = useCreateAuditExport()
  const remove = useDeleteAuditExport()
  const cleanup = useCleanupAuditExports()

  const onCreate = (format: AuditExportFormat) => {
    create.mutate({ format, query })
  }

  const items = exports.data?.items ?? []

  return (
    <Card>
      <CardHeader
        title="Stored exports"
        subtitle="Exports are written to the configured backend and expire after 30 days."
        action={
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => onCreate('csv')}
              disabled={create.isPending}
            >
              {create.isPending && create.variables?.format === 'csv' ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Upload size={13} />
              )}
              Export CSV
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => onCreate('json')}
              disabled={create.isPending}
            >
              {create.isPending && create.variables?.format === 'json' ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Upload size={13} />
              )}
              Export JSON
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => cleanup.mutate()}
              disabled={cleanup.isPending}
            >
              {cleanup.isPending ? <Loader2 size={13} className="animate-spin" /> : 'Cleanup'}
            </Button>
          </div>
        }
      />
      <CardBody className="p-0">
        {exports.isLoading ? (
          <div className="px-5 pb-5 space-y-2">
            {Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
          </div>
        ) : items.length === 0 ? (
          <div className="px-5 py-8 text-center text-xs text-ink-muted">
            No exports yet. Create one to archive the current filter selection.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-ink-muted">
                <th className="px-5 py-2 font-medium">Created</th>
                <th className="px-5 py-2 font-medium">Format</th>
                <th className="px-5 py-2 font-medium">Backend</th>
                <th className="px-5 py-2 font-medium text-right">Records</th>
                <th className="px-5 py-2 font-medium text-right">Size</th>
                <th className="px-5 py-2 font-medium">Status</th>
                <th className="px-5 py-2 font-medium">Expires</th>
                <th className="px-5 py-2 font-medium text-right"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.id} className="border-b border-border last:border-b-0">
                  <td className="px-5 py-2.5 text-ink-muted text-xs">{formatDateTime(e.createdAt)}</td>
                  <td className="px-5 py-2.5 text-ink-muted text-xs uppercase">{e.format}</td>
                  <td className="px-5 py-2.5 text-ink-muted text-xs uppercase">{e.storageBackend}</td>
                  <td className="px-5 py-2.5 text-right tabular-nums">{e.recordCount}</td>
                  <td className="px-5 py-2.5 text-right tabular-nums">{formatBytes(e.sizeBytes)}</td>
                  <td className="px-5 py-2.5">
                    <Badge tone={STATUS_TONE[e.status]}>{e.status}</Badge>
                  </td>
                  <td className="px-5 py-2.5 text-ink-subtle text-xs">
                    {new Date(e.expiresAt).toLocaleDateString()}
                  </td>
                  <td className="px-5 py-2.5 text-right">
                    <div className="inline-flex items-center gap-2">
                      {e.downloadUrl ? (
                        <a
                          href={e.downloadUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="rounded p-1 text-ink-subtle hover:text-ink"
                          aria-label="Download export"
                        >
                          <Download size={13} />
                        </a>
                      ) : null}
                      <button
                        type="button"
                        onClick={() => {
                          if (window.confirm('Delete this export? The stored file will be removed.')) {
                            remove.mutate(e.id)
                          }
                        }}
                        className="rounded p-1 text-ink-subtle hover:text-danger"
                        aria-label="Delete export"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardBody>
    </Card>
  )
}