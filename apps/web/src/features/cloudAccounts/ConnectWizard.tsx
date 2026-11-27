import { useState } from 'react'
import { Check, Copy, ExternalLink, Loader2 } from 'lucide-react'
import { clsx } from 'clsx'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { useConnectAws, useConnectAzure, useVerifyCloudAccount } from './hooks'
import type { AwsConnectResult, AzureConnectResult } from './api'

type Provider = 'AWS' | 'Azure'
type Step = 'provider' | 'details' | 'setup' | 'verify'

const ENVIRONMENT_OPTIONS = [
  { value: 'production', label: 'Production' },
  { value: 'staging', label: 'Staging' },
  { value: 'development', label: 'Development' },
  { value: 'sandbox', label: 'Sandbox' },
]

const AWS_REGION_OPTIONS = [
  { value: 'us-east-1', label: 'us-east-1' },
  { value: 'us-west-2', label: 'us-west-2' },
  { value: 'eu-west-1', label: 'eu-west-1' },
  { value: 'ap-south-1', label: 'ap-south-1' },
]

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // ignore
    }
  }
  return (
    <button
      type="button"
      onClick={copy}
      className="inline-flex items-center gap-1 text-[11px] text-ink-muted hover:text-ink"
      aria-label="Copy"
    >
      {copied ? <Check size={11} /> : <Copy size={11} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

export function ConnectWizard({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [step, setStep] = useState<Step>('provider')
  const [provider, setProvider] = useState<Provider | null>(null)

  const [name, setName] = useState('')
  const [environment, setEnvironment] = useState('production')

  const [awsAccountId, setAwsAccountId] = useState('')
  const [awsRoleArn, setAwsRoleArn] = useState('')
  const [awsRegions, setAwsRegions] = useState<string[]>(['us-east-1'])

  const [azureSubscription, setAzureSubscription] = useState('')
  const [azureTenant, setAzureTenant] = useState('')
  const [azureClientId, setAzureClientId] = useState('')
  const [azureClientSecret, setAzureClientSecret] = useState('')

  const [awsResult, setAwsResult] = useState<AwsConnectResult | null>(null)
  const [azureResult, setAzureResult] = useState<AzureConnectResult | null>(null)
  const [accountId, setAccountId] = useState<string | null>(null)
  const [verifyMessage, setVerifyMessage] = useState<string | null>(null)

  const connectAws = useConnectAws()
  const connectAzure = useConnectAzure()
  const verify = useVerifyCloudAccount()

  const reset = () => {
    setStep('provider')
    setProvider(null)
    setName('')
    setEnvironment('production')
    setAwsAccountId('')
    setAwsRoleArn('')
    setAwsRegions(['us-east-1'])
    setAzureSubscription('')
    setAzureTenant('')
    setAzureClientId('')
    setAzureClientSecret('')
    setAwsResult(null)
    setAzureResult(null)
    setAccountId(null)
    setVerifyMessage(null)
    connectAws.reset()
    connectAzure.reset()
    verify.reset()
  }

  const close = () => {
    reset()
    onClose()
  }

  const submitAws = async () => {
    const result = await connectAws.mutateAsync({
      name,
      accountIdentifier: awsAccountId,
      roleArn: awsRoleArn,
      environment,
      regions: awsRegions,
    })
    setAwsResult(result)
    setAccountId(result.id)
    setStep('setup')
  }

  const submitAzure = async () => {
    const result = await connectAzure.mutateAsync({
      name,
      subscriptionId: azureSubscription,
      tenantId: azureTenant,
      clientId: azureClientId,
      clientSecret: azureClientSecret,
      environment,
    })
    setAzureResult(result)
    setAccountId(result.id)
    setStep('setup')
  }

  const runVerify = async () => {
    if (!accountId) return
    const result = await verify.mutateAsync(accountId)
    setVerifyMessage(result.message)
    if (result.ok) {
      setTimeout(close, 1200)
    }
  }

  const canSubmitAws =
    name.trim().length > 0 &&
    /^\d{12}$/.test(awsAccountId) &&
    awsRoleArn.startsWith('arn:aws:iam::') &&
    awsRegions.length > 0

  const canSubmitAzure =
    name.trim().length > 0 &&
    azureSubscription.trim().length > 0 &&
    azureTenant.trim().length > 0 &&
    azureClientId.trim().length > 0 &&
    azureClientSecret.trim().length > 0

  const title =
    step === 'provider'
      ? 'Connect a cloud account'
      : step === 'details'
        ? `Connect ${provider}`
        : step === 'setup'
          ? `Configure ${provider} access`
          : 'Verify connection'

  const description =
    step === 'provider'
      ? 'Connections are read-only by default. Execution roles are configured separately and require security review.'
      : step === 'details'
        ? provider === 'AWS'
          ? 'Provide the AWS account ID and the role ARN you will create for CloudFinOps AI.'
          : 'Provide the Azure subscription and service principal details.'
        : step === 'setup'
          ? 'Apply the following configuration in your cloud console, then verify.'
          : 'CloudFinOps AI will make a read-only API call to confirm access.'

  return (
    <Modal
      open={open}
      onClose={close}
      title={title}
      description={description}
      footer={
        <>
          {step !== 'provider' ? (
            <Button variant="ghost" onClick={() => setStep(step === 'verify' ? 'setup' : 'provider')} disabled={connectAws.isPending || connectAzure.isPending || verify.isPending}>
              Back
            </Button>
          ) : (
            <Button variant="ghost" onClick={close}>Cancel</Button>
          )}

          {step === 'provider' ? (
            <Button
              variant="primary"
              disabled={!provider}
              onClick={() => setStep('details')}
            >
              Continue
            </Button>
          ) : step === 'details' ? (
            <Button
              variant="primary"
              disabled={provider === 'AWS' ? !canSubmitAws : !canSubmitAzure}
              onClick={provider === 'AWS' ? submitAws : submitAzure}
            >
              {connectAws.isPending || connectAzure.isPending ? (
                <span className="inline-flex items-center gap-1.5">
                  <Loader2 size={13} className="animate-spin" />
                  Creating…
                </span>
              ) : (
                'Create connection'
              )}
            </Button>
          ) : step === 'setup' ? (
            <Button variant="primary" onClick={() => setStep('verify')}>
              I've applied this
            </Button>
          ) : (
            <Button
              variant="primary"
              onClick={runVerify}
              disabled={verify.isPending || !accountId}
            >
              {verify.isPending ? (
                <span className="inline-flex items-center gap-1.5">
                  <Loader2 size={13} className="animate-spin" />
                  Verifying…
                </span>
              ) : (
                'Verify connection'
              )}
            </Button>
          )}
        </>
      }
    >
      {step === 'provider' ? (
        <div className="space-y-3">
          <p className="text-xs text-ink-muted">Choose a provider to connect.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {(['AWS', 'Azure'] as Provider[]).map((p) => (
              <button
                key={p}
                onClick={() => setProvider(p)}
                className={clsx(
                  'rounded-md border px-4 py-3 text-left transition-colors',
                  provider === p
                    ? 'border-accent bg-accent-soft'
                    : 'border-border bg-surface hover:border-border-strong',
                )}
              >
                <p className="text-sm font-medium text-ink">{p === 'AWS' ? 'Amazon Web Services' : 'Microsoft Azure'}</p>
                <p className="mt-1 text-xs text-ink-muted">
                  {p === 'AWS'
                    ? 'Cross-account IAM role with external ID validation.'
                    : 'Service principal with Cost Management Reader.'}
                </p>
              </button>
            ))}
          </div>
        </div>
      ) : step === 'details' ? (
        <div className="space-y-4">
          <Input label="Display name" placeholder="AWS Production" value={name} onChange={(e) => setName(e.target.value)} />
          <Select
            label="Environment"
            value={environment}
            onChange={setEnvironment}
            options={ENVIRONMENT_OPTIONS}
          />
          {provider === 'AWS' ? (
            <>
              <Input
                label="AWS account ID"
                placeholder="123456789012"
                value={awsAccountId}
                onChange={(e) => setAwsAccountId(e.target.value.replace(/\D/g, '').slice(0, 12))}
              />
              <Input
                label="IAM role ARN"
                placeholder="arn:aws:iam::123456789012:role/CloudFinOpsReadOnly"
                value={awsRoleArn}
                onChange={(e) => setAwsRoleArn(e.target.value)}
              />
              <div>
                <p className="text-[11px] font-medium text-ink-muted uppercase tracking-wide">Regions</p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {AWS_REGION_OPTIONS.map((r) => {
                    const active = awsRegions.includes(r.value)
                    return (
                      <button
                        key={r.value}
                        type="button"
                        onClick={() =>
                          setAwsRegions((prev) =>
                            active ? prev.filter((x) => x !== r.value) : [...prev, r.value],
                          )
                        }
                        className={clsx(
                          'rounded border px-2.5 py-1 text-xs transition-colors',
                          active
                            ? 'border-accent bg-accent-soft text-accent'
                            : 'border-border bg-surface text-ink-muted hover:text-ink',
                        )}
                      >
                        {r.label}
                      </button>
                    )
                  })}
                </div>
              </div>
            </>
          ) : (
            <>
              <Input
                label="Subscription ID"
                value={azureSubscription}
                onChange={(e) => setAzureSubscription(e.target.value)}
              />
              <Input
                label="Tenant ID"
                value={azureTenant}
                onChange={(e) => setAzureTenant(e.target.value)}
              />
              <Input
                label="Client ID (Application ID)"
                value={azureClientId}
                onChange={(e) => setAzureClientId(e.target.value)}
              />
              <Input
                label="Client secret"
                type="password"
                value={azureClientSecret}
                onChange={(e) => setAzureClientSecret(e.target.value)}
              />
            </>
          )}
          {connectAws.isError || connectAzure.isError ? (
            <p className="text-xs text-danger">
              {(connectAws.error as Error | null)?.message ?? (connectAzure.error as Error | null)?.message}
            </p>
          ) : null}
        </div>
      ) : step === 'setup' && provider === 'AWS' && awsResult ? (
        <div className="space-y-4 text-sm">
          <div>
            <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">External ID</p>
            <div className="mt-1 flex items-center justify-between gap-2 rounded border border-border bg-surface-muted px-3 py-2">
              <code className="text-xs font-mono break-all">{awsResult.externalId}</code>
              <CopyButton value={awsResult.externalId} />
            </div>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Role ARN</p>
            <div className="mt-1 flex items-center justify-between gap-2 rounded border border-border bg-surface-muted px-3 py-2">
              <code className="text-xs font-mono break-all">{awsResult.roleArn}</code>
              <CopyButton value={awsResult.roleArn} />
            </div>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Trust policy</p>
            <div className="mt-1 relative rounded border border-border bg-surface-muted px-3 py-2">
              <pre className="text-[11px] font-mono whitespace-pre-wrap break-all">
{JSON.stringify(awsResult.trustPolicy, null, 2)}
              </pre>
              <div className="mt-1 flex justify-end">
                <CopyButton value={JSON.stringify(awsResult.trustPolicy, null, 2)} />
              </div>
            </div>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Managed policies</p>
            <ul className="mt-1 space-y-0.5 text-xs text-ink-muted font-mono">
              <li>arn:aws:iam::aws:policy/ReadOnlyAccess</li>
              <li>arn:aws:iam::aws:policy/AWSBillingReadOnlyAccess</li>
            </ul>
          </div>
          <a
            href="https://console.aws.amazon.com/iam/home#/roles/create"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-accent hover:underline"
          >
            Open IAM console to create the role <ExternalLink size={12} />
          </a>
        </div>
      ) : step === 'setup' && provider === 'Azure' && azureResult ? (
        <div className="space-y-4 text-sm">
          <div>
            <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Subscription ID</p>
            <div className="mt-1 flex items-center justify-between gap-2 rounded border border-border bg-surface-muted px-3 py-2">
              <code className="text-xs font-mono break-all">{azureResult.subscriptionId}</code>
              <CopyButton value={azureResult.subscriptionId} />
            </div>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide font-medium text-ink-muted">Grant Cost Management Reader</p>
            <div className="mt-1 relative rounded border border-border bg-surface-muted px-3 py-2">
              <pre className="text-[11px] font-mono whitespace-pre-wrap break-all">{azureResult.azCliCommand}</pre>
              <div className="mt-1 flex justify-end">
                <CopyButton value={azureResult.azCliCommand} />
              </div>
            </div>
          </div>
          <p className="text-xs text-ink-muted">{azureResult.note}</p>
        </div>
      ) : (
        <div className="space-y-3 text-sm">
          {verify.isPending ? (
            <p className="text-ink-muted">Verifying connection…</p>
          ) : verifyMessage ? (
            <div
              className={clsx(
                'rounded border px-3 py-2 text-sm',
                verify.data?.ok ? 'border-success-soft bg-success-soft text-ink' : 'border-danger-soft bg-danger-soft text-ink',
              )}
            >
              {verifyMessage}
            </div>
          ) : (
            <p className="text-ink-muted">Click Verify connection to make a read-only API call.</p>
          )}
        </div>
      )}
    </Modal>
  )
}