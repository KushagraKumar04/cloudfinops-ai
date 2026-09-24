import { useState, useRef, useEffect, type KeyboardEvent } from 'react'
import { SendHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/Button'

interface Props {
  onSend: (text: string) => void
  disabled?: boolean
}

export function Composer({ onSend, disabled }: Props) {
  const [value, setValue] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }, [value])

  const submit = () => {
    const text = value.trim()
    if (!text || disabled) return
    onSend(text)
    setValue('')
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="flex items-end gap-2 rounded-md border border-border bg-surface px-3 py-2 focus-within:border-accent">
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        rows={1}
        placeholder="Ask about spend, resources, savings, or forecasts…"
        className="flex-1 resize-none bg-transparent text-sm text-ink placeholder:text-ink-subtle focus:outline-none"
        disabled={disabled}
      />
      <Button
        variant="primary"
        size="sm"
        onClick={submit}
        disabled={disabled || !value.trim()}
        aria-label="Send message"
      >
        <SendHorizontal size={14} />
      </Button>
    </div>
  )
}