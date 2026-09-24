import { clsx } from 'clsx'
import { Search } from 'lucide-react'
import type { InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  leadingIcon?: boolean
  className?: string
}

export function Input({ label, leadingIcon, className, ...rest }: InputProps) {
  return (
    <label className={clsx('inline-flex flex-col gap-1', className)}>
      {label ? (
        <span className="text-[11px] font-medium text-ink-muted uppercase tracking-wide">{label}</span>
      ) : null}
      <span className="relative flex items-center">
        {leadingIcon ? <Search size={14} className="absolute left-2.5 text-ink-subtle" /> : null}
        <input
          className={clsx(
            'h-9 w-full rounded border border-border bg-surface text-sm text-ink placeholder:text-ink-subtle focus:border-accent focus:outline-none',
            leadingIcon ? 'pl-8 pr-2.5' : 'px-2.5',
          )}
          {...rest}
        />
      </span>
    </label>
  )
}   