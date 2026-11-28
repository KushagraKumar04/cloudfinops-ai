import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { formatCurrency } from '@/lib/format'
import type { ForecastPoint } from './types'

interface Props {
  data: ForecastPoint[] | undefined
  budget: number
  isLoading: boolean
  isError: boolean
  onRetry: () => void
}

export function ForecastChart({ data, budget, isLoading, isError, onRetry }: Props) {
  return (
    <Card>
      <CardHeader title="Actual vs forecast" subtitle="Historical spend with projection band" />
      <CardBody>
        {isLoading ? (
          <Skeleton className="h-72 w-full" />
        ) : isError ? (
          <StateBlock
            variant="error"
            title="Could not load forecast"
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
          <StateBlock variant="empty" title="No forecast data" />
        ) : (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -16 }}>
                <defs>
                  <linearGradient id="fcBand" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2563EB" stopOpacity={0.12} />
                    <stop offset="100%" stopColor="#2563EB" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#EFEDE8" vertical={false} />
                <XAxis
                  dataKey="date"
                  tickFormatter={(d: string) => d.slice(5)}
                  stroke="#9A9A9A"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  minTickGap={32}
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
                  formatter={(v: number, name) => {
                    if (name === 'Confidence band') return [null, null]
                    return [formatCurrency(v), name]
                  }}
                />
                <Area type="monotone" dataKey="upper" stroke="none" fill="url(#fcBand)" name="Confidence band" />
                <Area type="monotone" dataKey="lower" stroke="none" fill="#FFFFFF" fillOpacity={1} />
                <ReferenceLine y={budget} stroke="#D97706" strokeDasharray="4 3" label={{ value: 'Budget', position: 'right', fontSize: 10, fill: '#D97706' }} />
                <Line type="monotone" dataKey="actual" stroke="#1A1A1A" strokeWidth={2} dot={false} name="Actual" />
                <Line type="monotone" dataKey="forecast" stroke="#2563EB" strokeWidth={2} strokeDasharray="4 4" dot={false} name="Forecast" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardBody>
    </Card>
  )
}