import { clsx } from 'clsx'
import { ToolCallTrace } from './ToolCallTrace'
import { StructuredResponse } from './StructuredResponse'
import type { ChatMessage as ChatMessageType } from './types'

interface Props {
  message: ChatMessageType
  onFollowUp: (q: string) => void
}

export function ChatMessage({ message, onFollowUp }: Props) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-md border border-border bg-surface px-3.5 py-2 text-sm text-ink">
          {message.text}
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-sm bg-accent text-[10px] font-semibold text-white">
        AI
      </div>
      <div className={clsx('min-w-0 flex-1 space-y-4')}>
        {(message.plan || (message.toolCalls && message.toolCalls.length > 0) || message.status !== 'complete') ? (
          <ToolCallTrace plan={message.plan} toolCalls={message.toolCalls} status={message.status ?? 'complete'} />
        ) : null}
        {message.response ? <StructuredResponse response={message.response} onFollowUp={onFollowUp} /> : null}
      </div>
    </div>
  )
}