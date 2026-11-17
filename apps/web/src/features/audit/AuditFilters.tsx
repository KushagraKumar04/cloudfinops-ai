import { Input } from '@/components/ui/Input'
import { Select, type SelectOption } from '@/components/ui/Select'
import { CATEGORY_LABEL } from './queryParams'
import type { AuditCategory, AuditQueryParams, AuditSeverity } from './types'

const CATEGORY_OPTIONS: SelectOption[] = [
  { value: 'all', label: 'All categories' },
  ...(Object.keys(CATEGORY_LABEL) as AuditCategory[]).map((c) => ({ value: c, label: CATEGORY_LABEL[c] })),
]

const SEVERITY_OPTIONS: SelectOption[] = [
  { value: 'all', label: 'Any severity' },
  { value: 'info', label: 'Info' },
  { value: 'warning', label: 'Warning' },
  { value: 'critical', label: 'Critical' },
]

export function AuditFilters({
  value,
  onChange,
}: {
  value: AuditQueryParams
  onChange: (next: AuditQueryParams) => void
}) {
  return (
    <div className="flex flex-wrap items-end gap-3 rounded-md border border-border bg-surface px-4 py-3">
      <Input
        label="Search"
        leadingIcon
        placeholder="Actor, action, subject"
        value={value.search}
        onChange={(e) => onChange({ ...value, search: e.target.value, page: 1 })}
        className="w-full sm:w-72"
      />
      <Select
        label="Category"
        value={value.category}
        onChange={(v) => onChange({ ...value, category: v as AuditCategory | 'all', page: 1 })}
        options={CATEGORY_OPTIONS}
      />
      <Select
        label="Severity"
        value={value.severity}
        onChange={(v) => onChange({ ...value, severity: v as AuditSeverity | 'all', page: 1 })}
        options={SEVERITY_OPTIONS}
      />
    </div>
  )
}