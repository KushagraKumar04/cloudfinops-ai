import type { ReactNode } from 'react'
import { AlertCircle, Inbox } from 'lucide-react'

interface StateBlockProps {
  variant: 'empty' | 'error'
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export function StateBlock({ variant, title, description, action, className }: StateBlockProps) {
  const Icon = variant === 'error' ? AlertCircle : Inbox
  const iconClass = variant === 'error' ? 'text-danger' : 'text-ink-subtle'
  return (
    <div className={`flex flex-col items-center justify-center text-center px-6 py-10 ${className ?? ''}`}>
      <Icon size={22} className={iconClass} strokeWidth={1.75} />
      <p className="mt-3 text-sm font-medium text-ink">{title}</p>
      {description ? <p className="mt-1 text-xs text-ink-muted max-w-sm">{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  )
}