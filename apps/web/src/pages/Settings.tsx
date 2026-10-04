import { useEffect, useState } from 'react'
import { PageHeader } from '@/components/ui/PageHeader'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select, type SelectOption } from '@/components/ui/Select'
import { Toggle } from '@/components/ui/Toggle'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { useSettings, useUpdateLlm, useUpdatePolicies, useUpdateThresholds } from '@/features/settings/hooks'
import { useAuth } from '@/features/auth/useAuth'
import type { LlmConfig, PolicyRule, ThresholdRule } from '@/features/settings/types'

const PROVIDER_OPTIONS: SelectOption[] = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'azure-openai', label: 'Azure OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
]

export function Settings() {
  const { data, isLoading, isError, refetch } = useSettings()
  const { can } = useAuth()
  const canEdit = can('edit_settings')

  const [policies, setPolicies] = useState<PolicyRule[]>([])
  const [thresholds, setThresholds] = useState<ThresholdRule[]>([])
  const [llm, setLlm] = useState<LlmConfig | null>(null)

  const savePolicies = useUpdatePolicies()
  const saveThresholds = useUpdateThresholds()
  const saveLlm = useUpdateLlm()

  useEffect(() => {
    if (data) {
      setPolicies(data.policies)
      setThresholds(data.thresholds)
      setLlm(data.llm)
    }
  }, [data])

  if (isLoading) {
    return (
      <>
        <PageHeader title="Settings" description="Policy, thresholds, and AI configuration." />
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-40 w-full" />)}
        </div>
      </>
    )
  }

  if (isError || !data || !llm) {
    return (
      <>
        <PageHeader title="Settings" description="Policy, thresholds, and AI configuration." />
        <Card>
          <StateBlock
            variant="error"
            title="Could not load settings"
            action={<Button size="sm" onClick={() => refetch()}>Retry</Button>}
          />
        </Card>
      </>
    )
  }

  const policiesDirty = JSON.stringify(policies) !== JSON.stringify(data.policies)
  const thresholdsDirty = JSON.stringify(thresholds) !== JSON.stringify(data.thresholds)
  const llmDirty = JSON.stringify(llm) !== JSON.stringify(data.llm)

  return (
    <>
      <PageHeader
        title="Settings"
        description={
          canEdit
            ? 'Policy, thresholds, and AI configuration. Changes apply to the FinOps engine on the next analysis run.'
            : 'Read-only view. Your role does not allow editing settings.'
        }
      />

      <section className="space-y-4">
        <Card>
          <CardHeader
            title="Policy engine"
            subtitle="Policies are code and configuration, not prompt text. They run after the LLM proposes an action."
            action={
              canEdit && policiesDirty ? (
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="ghost" onClick={() => setPolicies(data.policies)}>Discard</Button>
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => savePolicies.mutate(policies)}
                    disabled={savePolicies.isPending}
                  >
                    {savePolicies.isPending ? 'Saving…' : 'Save policies'}
                  </Button>
                </div>
              ) : null
            }
          />
          <CardBody className="space-y-4 pt-0">
            {policies.map((p, idx) => (
              <div key={p.id} className="border-b border-border last:border-b-0 pb-4 last:pb-0">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-ink">{p.scope}</p>
                      <code className="text-[10px] font-mono text-ink-subtle">{p.id}</code>
                    </div>
                    <p className="mt-1 text-xs text-ink-muted leading-relaxed max-w-2xl">{p.description}</p>
                  </div>
                  <Toggle
                    checked={p.enabled}
                    onChange={(enabled) =>
                      setPolicies((prev) => prev.map((x, i) => (i === idx ? { ...x, enabled } : x)))
                    }
                    label="Enabled"
                  />
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-ink-muted">
                  <label className="inline-flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={p.requiresApproval}
                      onChange={(e) =>
                        setPolicies((prev) =>
                          prev.map((x, i) => (i === idx ? { ...x, requiresApproval: e.target.checked } : x)),
                        )
                      }
                      className="h-3.5 w-3.5"
                    />
                    Requires human approval
                  </label>
                  <label className="inline-flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={p.blockAutoExecution}
                      onChange={(e) =>
                        setPolicies((prev) =>
                          prev.map((x, i) => (i === idx ? { ...x, blockAutoExecution: e.target.checked } : x)),
                        )
                      }
                      className="h-3.5 w-3.5"
                    />
                    Block automatic execution
                  </label>
                </div>
              </div>
            ))}
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="FinOps thresholds"
            subtitle="Values used by deterministic rules. Thresholds are configuration, not prompts."
            action={
              canEdit && thresholdsDirty ? (
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="ghost" onClick={() => setThresholds(data.thresholds)}>Discard</Button>
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => saveThresholds.mutate(thresholds)}
                    disabled={saveThresholds.isPending}
                  >
                    {saveThresholds.isPending ? 'Saving…' : 'Save thresholds'}
                  </Button>
                </div>
              ) : null
            }
          />
          <CardBody className="pt-0">
            <div className="space-y-4">
              {thresholds.map((t, idx) => (
                <div key={t.id} className="border-b border-border last:border-b-0 pb-4 last:pb-0">
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink">{t.label}</p>
                      <p className="mt-1 text-xs text-ink-muted leading-relaxed max-w-2xl">{t.description}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <input
                        type="number"
                        min={t.minimum}
                        max={t.maximum}
                        value={t.value}
                        onChange={(e) => {
                          const v = Number(e.target.value)
                          if (!Number.isFinite(v)) return
                          setThresholds((prev) => prev.map((x, i) => (i === idx ? { ...x, value: v } : x)))
                        }}
                        className="h-9 w-24 rounded border border-border bg-surface px-2.5 text-sm text-ink tabular-nums focus:border-accent focus:outline-none"
                      />
                      <span className="text-xs text-ink-muted tabular-nums w-12">{t.unit}</span>
                    </div>
                  </div>
                  <p className="mt-1 text-[11px] text-ink-subtle">
                    Range {t.minimum} – {t.maximum} {t.unit}
                  </p>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="AI configuration"
            subtitle="Model routing, caching, and prompt versioning. The LLM is never the source of truth for billing."
            action={
              canEdit && llmDirty ? (
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="ghost" onClick={() => setLlm(data.llm)}>Discard</Button>
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => saveLlm.mutate(llm)}
                    disabled={saveLlm.isPending}
                  >
                    {saveLlm.isPending ? 'Saving…' : 'Save AI settings'}
                  </Button>
                </div>
              ) : null
            }
          />
          <CardBody className="pt-0 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select
                label="Provider"
                value={llm.provider}
                onChange={(v) => setLlm({ ...llm, provider: v as LlmConfig['provider'] })}
                options={PROVIDER_OPTIONS}
              />
              <Input
                label="Model"
                value={llm.model}
                onChange={(e) => setLlm({ ...llm, model: e.target.value })}
              />
              <Input
                label="Temperature"
                type="number"
                min={0}
                max={1}
                step={0.05}
                value={String(llm.temperature)}
                onChange={(e) => {
                  const v = Number(e.target.value)
                  if (Number.isFinite(v)) setLlm({ ...llm, temperature: v })
                }}
              />
              <Input
                label="Max tokens"
                type="number"
                min={256}
                max={16384}
                value={String(llm.maxTokens)}
                onChange={(e) => {
                  const v = Number(e.target.value)
                  if (Number.isFinite(v)) setLlm({ ...llm, maxTokens: v })
                }}
              />
              <Input
                label="Prompt version"
                value={llm.promptVersion}
                onChange={(e) => setLlm({ ...llm, promptVersion: e.target.value })}
              />
            </div>
            <div className="space-y-3 pt-2 border-t border-border">
              <Toggle
                checked={llm.cacheEnabled}
                onChange={(cacheEnabled) => setLlm({ ...llm, cacheEnabled })}
                label="Cache identical tool calls"
                description="Reduces token usage for repeated queries within a session."
              />
              <Toggle
                checked={llm.compactToolOutputs}
                onChange={(compactToolOutputs) => setLlm({ ...llm, compactToolOutputs })}
                label="Compact tool outputs"
                description="Strip verbose fields from tool responses before they enter the prompt."
              />
            </div>
            <div className="pt-2 border-t border-border space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-medium text-ink-muted uppercase tracking-wide">API key</span>
                {llm.apiKeyConfigured ? (
                  <Badge tone="success">Configured server-side</Badge>
                ) : (
                  <Badge tone="warning">Not configured</Badge>
                )}
              </div>
              <p className="text-[11px] text-ink-subtle">
                The API key is stored as an environment variable on the server. It is never sent to the browser, returned by any endpoint, or included in prompts.
              </p>
            </div>
          </CardBody>
        </Card>
      </section>
    </>
  )
}