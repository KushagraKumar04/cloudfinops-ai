import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { formatCurrency, formatDate } from '@/lib/format'
import type { Commitment } from './types'

const TYPE_LABEL: Record<string, string> = {
  reserved_instance: 'Reserved instance',
  savings_plan: 'Savings plan',
  reserved_vm: 'Reserved VM',
  reserved_capacity: 'Reserved capacity',
}

export function CommitmentTable({ items }: { items: Commitment[] }) {
  return (
    <Card>
      <CardHeader title="Active commitments" subtitle="Reserved instances and savings plans currently in effect" />
      <CardBody className="p-0">
        {items.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-ink-muted">No active commitments.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[880px]">
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-ink-muted">
                  <th className="px-5 py-2 font-medium">Service</th>
                  <th className="px-5 py-2 font-medium">Type</th>
                  <th className="px-5 py-2 font-medium">Term</th>
                  <th className="px-5 py-2 font-medium">Payment</th>
                  <th className="px-5 py-2 font-medium text-right">Monthly cost</th>
                  <th className="px-5 py-2 font-medium text-right">Savings</th>
                  <th className="px-5 py-2 font-medium">Utilization</th>
                  <th className="px-5 py-2 font-medium">Expires</th>
                </tr>
              </thead>
              <tbody>
                {items.map((c) => {
                  const util = Math.round(c.utilizationPct * 1000) / 10
                  const utilTone = util >= 85 ? 'success' : util >= 60 ? 'warning' : 'danger'
                  return (
                    <tr key={c.id} className="border-b border-border last:border-b-0">
                      <td className="px-5 py-2.5">
                        <div className="text-ink font-medium">{c.service}</div>
                        <div className="text-[11px] text-ink-subtle">{c.provider} · {c.region}</div>
                      </td>
                      <td className="px-5 py-2.5 text-ink-muted text-xs">{TYPE_LABEL[c.commitmentType] ?? c.commitmentType}</td>
                      <td className="px-5 py-2.5 text-ink-muted text-xs">{c.termMonths}mo</td>
                      <td className="px-5 py-2.5 text-ink-muted text-xs capitalize">{c.paymentOption.replace('_', ' ')}</td>
                      <td className="px-5 py-2.5 text-right tabular-nums">{formatCurrency(c.monthlyCost)}</td>
                      <td className="px-5 py-2.5 text-right text-success font-medium tabular-nums">
                        {formatCurrency(c.monthlySavings)}
                      </td>
                      <td className="px-5 py-2.5">
                        <div className="flex items-center gap-2">
                          <Badge tone={utilTone}>{util.toFixed(0)}%</Badge>
                        </div>
                      </td>
                      <td className="px-5 py-2.5 text-ink-muted text-xs">{formatDate(c.endDate)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardBody>
    </Card>
  )
}