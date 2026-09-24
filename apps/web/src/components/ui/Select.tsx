import { clsx } from 'clsx'

export interface SelectOption {
  value: string
  label: string
}

interface SelectProps {
  value: string
  onChange: (value: string) => void
  options: SelectOption[]
  label?: string
  className?: string
  ariaLabel?: string
}

export function Select({ value, onChange, options, label, className, ariaLabel }: SelectProps) {
  return (
    <label className={clsx('inline-flex flex-col gap-1', className)}>
      {label ? <span className="text-[11px] font-medium text-ink-muted uppercase tracking-wide">{label}</span> : null}
      <select
        aria-label={ariaLabel ?? label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded border border-border bg-surface px-2.5 pr-8 text-sm text-ink focus:border-accent focus:outline-none"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  )
}