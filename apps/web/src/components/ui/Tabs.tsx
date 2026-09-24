import { clsx } from 'clsx'

export interface TabItem<T extends string> {
  value: T
  label: string
}

interface TabsProps<T extends string> {
  value: T
  onChange: (value: T) => void
  items: TabItem<T>[]
  ariaLabel?: string
}

export function Tabs<T extends string>({ value, onChange, items, ariaLabel }: TabsProps<T>) {
  return (
    <div role="tablist" aria-label={ariaLabel} className="inline-flex items-center gap-1 rounded border border-border bg-surface p-0.5">
      {items.map((item) => {
        const active = item.value === value
        return (
          <button
            key={item.value}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(item.value)}
            className={clsx(
              'rounded-sm px-2.5 py-1 text-xs font-medium transition-colors',
              active ? 'bg-accent-soft text-accent' : 'text-ink-muted hover:text-ink',
            )}
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}