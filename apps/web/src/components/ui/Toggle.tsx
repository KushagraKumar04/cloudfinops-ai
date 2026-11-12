import { clsx } from 'clsx'

interface ToggleProps {
  checked: boolean
  onChange: (next: boolean) => void
  label?: string
  description?: string
  disabled?: boolean
}

export function Toggle({ checked, onChange, label, description, disabled }: ToggleProps) {
  return (
    <label className={clsx('flex items-start justify-between gap-4', disabled ? 'opacity-60' : 'cursor-pointer')}>
      {(label || description) ? (
        <div className="min-w-0">
          {label ? <p className="text-sm text-ink">{label}</p> : null}
          {description ? <p className="mt-0.5 text-xs text-ink-muted leading-relaxed">{description}</p> : null}
        </div>
      ) : null}
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={clsx(
          'relative shrink-0 mt-0.5 inline-flex h-5 w-9 items-center rounded-full border transition-colors',
          checked ? 'bg-accent border-accent' : 'bg-surface-muted border-border',
          'focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2',
        )}
      >
        <span
          className={clsx(
            'inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform',
            checked ? 'translate-x-[18px]' : 'translate-x-[3px]',
          )}
        />
      </button>
    </label>
  )
}