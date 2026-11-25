import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { formatCurrency } from '@/lib/format'
import type { CostQueryParams, CostTrendPoint } from './types'

interface Props {
  data: CostTrendPoint[] | undefined
  isLoading: boolean
  isError: boolean
  onRetry: () => void
  query: CostQueryParams
}

export function CostTrendChart({ data, isLoading, isError, onRetry, query }: Props) {
  const showAws = query.provider !== 'Azure'
  const showAzure = query.provider !== 'AWS'

  return (
    <Card>
      <CardHeader
        title="Spend trend"
        subtitle="Daily totals for the selected range"
      />
      <CardBody>
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : isError ? (
          <StateBlock
            variant="error"
            title="Could not load trend"
            description="The trend endpoint did not respond."
            action={
              <button
                onClick={onRetry}
                className="rounded border border-border bg-surface px-3 py-1.5 text-xs font-medium hover:border-border-strong"
              >
                Retry
              </button>
            }
          />
        ) : !data || data.length === 0 ? (
          <StateBlock
            variant="empty"
            title="No spend in range"
            description="Adjust the date range or clear filters to see data."
          />
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
                <CartesianGrid stroke="#EFEDE8" vertical={false} />
                <XAxis
                  dataKey="date"
                  tickFormatter={(d: string) => d.slice(5)}
                  stroke="#9A9A9A"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  minTickGap={24}
                />
                <YAxis
                  stroke="#9A9A9A"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v: number) => `$${(v / 1000).toFixed(1)}k`}
                />
                <Tooltip
                  contentStyle={{ border: '1px solid #E8E6E1', borderRadius: 6, fontSize: 12 }}
                  formatter={(v: number) => formatCurrency(v)}
                />
                {showAws ? <Line type="monotone" dataKey="aws" stroke="#2563EB" strokeWidth={2} dot={false} name="AWS" /> : null}
                {showAzure ? <Line type="monotone" dataKey="azure" stroke="#0F766E" strokeWidth={2} dot={false} name="Azure" /> : null}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardBody>
    </Card>
  )
}