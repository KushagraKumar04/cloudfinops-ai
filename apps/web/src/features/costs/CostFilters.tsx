import { Select, type SelectOption } from '@/components/ui/Select'
import { Tabs } from '@/components/ui/Tabs'
import { MOCK_ACCOUNTS, MOCK_SERVICES } from './mocks'
import type { CostQueryParams, CostRange, ProviderFilter } from './types'

const RANGE_ITEMS: { value: CostRange; label: string }[] = [
  { value: '7d', label: '7D' },
  { value: '30d', label: '30D' },
  { value: '90d', label: '90D' },
  { value: 'mtd', label: 'MTD' },
  { value: 'ytd', label: 'YTD' },
]

const PROVIDER_OPTIONS: SelectOption[] = [
  { value: 'all', label: 'All providers' },
  { value: 'AWS', label: 'AWS' },
  { value: 'Azure', label: 'Azure' },
]

const ACCOUNT_OPTIONS: SelectOption[] = [
  { value: 'all', label: 'All accounts' },
  ...MOCK_ACCOUNTS.map((a) => ({ value: a.id, label: a.name })),
]

const SERVICE_OPTIONS: SelectOption[] = [
  { value: 'all', label: 'All services' },
  ...MOCK_SERVICES.map((s) => ({ value: s, label: s })),
]

export function CostFilters({
  value,
  onChange,
}: {
  value: CostQueryParams
  onChange: (next: CostQueryParams) => void
}) {
  return (
    <div className="flex flex-wrap items-end gap-3 rounded-md border border-border bg-surface px-4 py-3">
      <div className="flex flex-col gap-1">
        <span className="text-[11px] font-medium text-ink-muted uppercase tracking-wide">Range</span>
        <Tabs<CostRange>
          ariaLabel="Cost range"
          value={value.range}
          onChange={(range) => onChange({ ...value, range })}
          items={RANGE_ITEMS}
        />
      </div>
      <Select
        label="Provider"
        value={value.provider}
        onChange={(v) => onChange({ ...value, provider: v as ProviderFilter })}
        options={PROVIDER_OPTIONS}
      />
      <Select
        label="Account"
        value={value.accountId}
        onChange={(accountId) => onChange({ ...value, accountId })}
        options={ACCOUNT_OPTIONS}
      />
      <Select
        label="Service"
        value={value.service}
        onChange={(service) => onChange({ ...value, service })}
        options={SERVICE_OPTIONS}
      />
    </div>
  )
}