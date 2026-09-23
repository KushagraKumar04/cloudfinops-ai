import { clsx } from 'clsx'
import type { HTMLAttributes, ReactNode } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
}

export function Card({ className, children, ...rest }: CardProps) {
  return (
    <div
      className={clsx(
        'bg-surface border border-border rounded-md',
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  )
}

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: string
  subtitle?: string
  action?: ReactNode
}) {
  return (
    <div className="flex items-start justify-between gap-4 px-5 pt-5 pb-3">
      <div>
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        {subtitle ? <p className="text-xs text-ink-muted mt-0.5">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  )
}

export function CardBody({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={clsx('px-5 pb-5', className)}>{children}</div>
}