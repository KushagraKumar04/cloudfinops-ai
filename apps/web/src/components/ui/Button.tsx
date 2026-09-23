import { clsx } from 'clsx'
import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
}

const variantClass: Record<Variant, string> = {
  primary: 'bg-accent text-white border-accent hover:bg-accent-hover',
  secondary: 'bg-surface text-ink border-border hover:border-border-strong',
  ghost: 'bg-transparent text-ink-muted border-transparent hover:bg-surface-muted hover:text-ink',
  danger: 'bg-danger text-white border-danger hover:opacity-90',
}

const sizeClass: Record<Size, string> = {
  sm: 'h-7 px-2.5 text-xs',
  md: 'h-9 px-3.5 text-sm',
}

export function Button({
  variant = 'secondary',
  size = 'md',
  className,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center gap-1.5 rounded border font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
        variantClass[variant],
        sizeClass[size],
        className,
      )}
      {...rest}
    />
  )
}