import { Check } from 'lucide-react'
import { clsx } from 'clsx'

interface CheckboxProps {
  checked: boolean
  onChange: (next: boolean) => void
  label?: string
  ariaLabel?: string
  indeterminate?: boolean
  disabled?: boolean
}

export function Checkbox({
  checked,
  onChange,
  label,
  ariaLabel,
  indeterminate,
  disabled,
}: CheckboxProps) {
  const active = checked || indeterminate
  return (
    <label className={clsx('inline-flex items-center gap-2', disabled ? 'opacity-50' : 'cursor-pointer')}>
      <span className="relative inline-flex">
        <input
          type="checkbox"
          className="sr-only"
          checked={checked}
          disabled={disabled}
          aria-label={ariaLabel ?? label}
          onChange={(e) => !disabled && onChange(e.target.checked)}
        />
        <span
          aria-hidden
          className={clsx(
            'inline-flex h-4 w-4 items-center justify-center rounded-sm border transition-colors',
            active ? 'border-accent bg-accent text-white' : 'border-border bg-surface',
          )}
        >
          {indeterminate && !checked ? (
            <span className="h-0.5 w-2 rounded-full bg-white" />
          ) : checked ? (
            <Check size={11} strokeWidth={3} />
          ) : null}
        </span>
      </span>
      {label ? <span className="text-xs text-ink">{label}</span> : null}
    </label>
  )
}