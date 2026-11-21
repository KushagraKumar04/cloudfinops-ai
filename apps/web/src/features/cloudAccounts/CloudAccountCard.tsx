import { Cloud, RefreshCw, ShieldCheck, KeyRound, CircleDot, Trash2 } from 'lucide-react'
import { clsx } from 'clsx'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { formatCurrency, formatDateTime, formatNumber } from '@/lib/format'
import { useSyncCloudAccount, useValidateCloudAccount, useVerifyCloudAccount } from './hooks'
import type { CloudAccount, ConnectionStatus, SyncScope } from './types'

const STATUS_TONE: Record<ConnectionStatus, 'success' | 'warning' | 'danger' | 'neutral'> = {
  connected: 'success',
  syncing: 'warning',
  error: 'danger',
  pending: 'warning',
  disabled: 'neutral',
}

const SCOPE_LABEL: Record<SyncScope, string> = {
  billing: 'Billing',
  inventory: 'Inventory',
  metrics: 'Metrics',
}

export function CloudAccountCard({
  account,
  onDelete,
  selected,
  onToggleSelect,
}: {
  account: CloudAccount
  onDelete?: (id: string, name: string) => void
  selected?: boolean
  onToggleSelect?: () => void
}) {
  const sync = useSyncCloudAccount()
  const validate = useValidateCloudAccount()
  const verify = useVerifyCloudAccount()
  const needsVerification = !account.connectionVerified && account.status !== 'connected'

  return (
    <Card>
      <CardHeader
        title={account.name}
        subtitle={`${account.provider} · ${account.identifier}`}
        action={
          <div className="flex items-center gap-2">
            {onToggleSelect ? (
              <input
                type="checkbox"
                checked={selected ?? false}
                onChange={onToggleSelect}
                className="h-3.5 w-3.5 rounded border-border accent-accent"
                aria-label={`Select ${account.name}`}
              />
            ) : null}
            <Badge tone={STATUS_TONE[account.status]}>{account.status}</Badge>
            {onDelete ? (
              <button
                type="button"
                onClick={() => onDelete(account.id, account.name)}
                className="rounded p-1 text-ink-subtle hover:text-danger"
                aria-label={`Disconnect ${account.name}`}
              >
                <Trash2 size={14} />
              </button>
            ) : null}
          </div>
        }
      />
      <CardBody className="pt-0 space-y-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Stat label="Environment" value={account.environment} capitalize />
          <Stat label="Resources" value={formatNumber(account.resourceCount)} />
          <Stat label="Monthly spend" value={formatCurrency(account.monthlySpend)} />
          <Stat label="Currency" value={account.currency} />
        </div>

        <div>
          <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Coverage</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {(Object.keys(account.coverage) as SyncScope[]).map((scope) => {
              const c = account.coverage[scope]
              return (
                <span
                  key={scope}
                  className={clsx(
                    'inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[11px]',
                    c.enabled ? 'border-border bg-surface text-ink' : 'border-border bg-surface-muted text-ink-muted',
                  )}
                >
                  <CircleDot size={9} className={c.enabled ? 'text-success' : 'text-ink-subtle'} />
                  <span>{SCOPE_LABEL[scope]}</span>
                  {c.lastSyncAt ? <span className="text-ink-subtle">· {formatDateTime(c.lastSyncAt)}</span> : null}
                </span>
              )
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="flex items-start gap-2 text-xs">
            <ShieldCheck size={13} className={account.readOnly ? 'text-success mt-0.5' : 'text-warning mt-0.5'} />
            <div>
              <p className="text-ink">{account.readOnly ? 'Read-only access' : 'Read-write access'}</p>
              <p className="text-ink-muted mt-0.5 break-all">
                {account.provider === 'AWS' && account.roleArn ? account.roleArn : null}
                {account.provider === 'Azure' && account.subscriptionId ? `subscription ${account.subscriptionId}` : null}
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2 text-xs">
            <KeyRound size={13} className={account.executionRoleConfigured ? 'text-success mt-0.5' : 'text-ink-subtle mt-0.5'} />
            <div>
              <p className="text-ink">
                {account.executionRoleConfigured ? 'Execution role configured' : 'No execution role'}
              </p>
              <p className="text-ink-muted mt-0.5">
                {account.executionRoleConfigured
                  ? 'Approved mutations can be executed with a separate role.'
                  : 'Execution is disabled for this account.'}
              </p>
            </div>
          </div>
        </div>

        {account.syncPhase && account.syncPhase !== 'complete' && account.status === 'syncing' ? (
          <div className="rounded border border-accent-soft bg-accent-soft/50 px-3 py-2 text-xs">
            <div className="flex items-center justify-between gap-3">
              <span className="text-ink font-medium capitalize">
                Syncing · {account.syncPhase}
              </span>
              <span className="text-ink-muted tabular-nums">{account.syncProgressPct}%</span>
            </div>
            <div className="mt-2 h-1 w-full rounded-full bg-white/60 overflow-hidden">
              <div
                className="h-full rounded-full bg-accent transition-all"
                style={{ width: `${Math.max(2, account.syncProgressPct)}%` }}
              />
            </div>
          </div>
        ) : (
          <div className="rounded border border-border bg-surface-muted/40 px-3 py-2 flex items-start gap-2 text-xs">
            <RefreshCw size={12} className="text-ink-subtle mt-0.5" />
            <div className="min-w-0">
              <p className="text-ink">
                Last sync {account.lastSyncAt ? formatDateTime(account.lastSyncAt) : 'never'}
                {account.lastSyncStatus ? (
                  <span
                    className={clsx(
                      'ml-2',
                      account.lastSyncStatus === 'success'
                        ? 'text-success'
                        : account.lastSyncStatus === 'partial'
                          ? 'text-warning'
                          : 'text-danger',
                    )}
                  >
                    · {account.lastSyncStatus}
                  </span>
                ) : null}
              </p>
              {account.lastSyncMessage ? <p className="text-ink-muted mt-0.5 truncate">{account.lastSyncMessage}</p> : null}
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          {needsVerification ? (
            <Button
              size="sm"
              variant="primary"
              onClick={() => verify.mutate(account.id)}
              disabled={verify.isPending}
            >
              {verify.isPending ? 'Verifying…' : 'Verify connection'}
            </Button>
          ) : (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => sync.mutate(account.id)}
              disabled={sync.isPending}
            >
              <RefreshCw size={13} className={sync.isPending ? 'animate-spin' : ''} />
              {sync.isPending ? 'Starting…' : 'Sync now'}
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => validate.mutate(account.id)}
            disabled={validate.isPending}
          >
            {validate.isPending ? 'Validating…' : 'Validate connection'}
          </Button>
          <span className="ml-auto text-[11px] text-ink-subtle">
            <Cloud size={11} className="inline -mt-0.5 mr-1" />
            {account.regions.length} region{account.regions.length === 1 ? '' : 's'} · {account.regions.join(', ')}
          </span>
        </div>
      </CardBody>
    </Card>
  )
}

function Stat({ label, value, capitalize }: { label: string; value: string; capitalize?: boolean }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">{label}</p>
      <p className={clsx('mt-0.5 text-sm text-ink tabular-nums', capitalize ? 'capitalize' : '')}>{value}</p>
    </div>
  )
}