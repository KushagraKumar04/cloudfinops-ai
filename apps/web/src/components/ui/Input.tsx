import { clsx } from 'clsx'
import { Search } from 'lucide-react'
import type { InputHTMLAttributes, ReactNode } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  leadingIcon?: boolean
  trailing?: ReactNode
  hint?: string
  error?: string
  className?: string
}

export function Input({ label, leadingIcon, trailing, hint, error, className, ...rest }: InputProps) {
  return (
    <label className={clsx('flex flex-col gap-1', className)}>
      {label ? (
        <span className="text-[11px] font-medium text-ink-muted uppercase tracking-wide">{label}</span>
      ) : null}
      <span
        className={clsx(
          'relative flex items-center rounded border bg-surface transition-colors',
          error ? 'border-danger' : 'border-border focus-within:border-accent',
        )}
      >
        {leadingIcon ? <Search size={14} className="absolute left-2.5 text-ink-subtle pointer-events-none" /> : null}
        <input
          className={clsx(
            'h-9 w-full bg-transparent text-sm text-ink placeholder:text-ink-subtle focus:outline-none',
            leadingIcon ? 'pl-8' : 'pl-2.5',
            trailing ? 'pr-9' : 'pr-2.5',
          )}
          {...rest}
        />
        {trailing ? (
          <span className="absolute right-1.5 flex items-center">
            {trailing}
          </span>
        ) : null}
      </span>
      {error ? (
        <span className="text-[11px] text-danger">{error}</span>
      ) : hint ? (
        <span className="text-[11px] text-ink-subtle">{hint}</span>
      ) : null}
    </label>
  )
}