import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useAuth } from '@/features/auth/useAuth'
import { listOAuthProviders, oauthAuthorizeUrl, type OAuthProviderInfo } from '@/features/auth/oauth'

export function Login() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: string } }
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [providers, setProviders] = useState<OAuthProviderInfo[]>([])

  useEffect(() => {
    listOAuthProviders().then(setProviders).catch(() => undefined)
  }, [])

  if (isAuthenticated) {
    return <Navigate to={location.state?.from ?? '/'} replace />
  }

  const enabledProviders = providers.filter((p) => p.enabled)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await login({ email: email.trim(), password })
      navigate(location.state?.from ?? '/', { replace: true })
    } catch (err) {
      setError((err as Error).message || 'Could not sign in')
    } finally {
      setBusy(false)
    }
  }

  const togglePassword = () => setShowPassword((v) => !v)

  return (
    <div className="min-h-screen bg-canvas flex">
      <div className="hidden lg:flex lg:w-[44%] border-r border-border bg-surface">
        <div className="flex flex-col justify-between w-full p-12">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-sm bg-accent" aria-hidden />
            <span className="text-base font-semibold tracking-tight text-ink">CloudFinOps AI</span>
          </div>
          <div className="max-w-md">
            <p className="text-2xl font-semibold text-ink tracking-tight leading-snug">
              Investigate cost changes with evidence, not guesswork.
            </p>
            <p className="mt-4 text-sm text-ink-muted leading-relaxed">
              Connect AWS and Azure. Ingest billing, inventory, and utilization. Reason over facts. Every recommendation carries its own evidence, savings calculation, and confidence level.
            </p>
            <ul className="mt-8 space-y-3 text-sm">
              <Bullet>Deterministic financial calculations</Bullet>
              <Bullet>AI proposes, humans approve, policy gates</Bullet>
              <Bullet>Read-only by default, least-privilege IAM</Bullet>
              <Bullet>Every privileged action is audited</Bullet>
            </ul>
          </div>
          <p className="text-[11px] text-ink-subtle">
            CloudFinOps AI · v0.1
          </p>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <div className="h-7 w-7 rounded-sm bg-accent" aria-hidden />
            <span className="text-base font-semibold tracking-tight">CloudFinOps AI</span>
          </div>

          <h1 className="text-xl font-semibold text-ink tracking-tight">Sign in</h1>
          <p className="mt-1 text-sm text-ink-muted">Access your organization's FinOps workspace.</p>

          <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
            <Input
              label="Email"
              type="email"
              autoComplete="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <Input
              label="Password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              trailing={
                <button
                  type="button"
                  onClick={togglePassword}
                  className="rounded p-1.5 text-ink-subtle hover:text-ink"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              }
            />
            {error ? <p className="text-xs text-danger">{error}</p> : null}
            <div className="flex justify-end">
              <Link to="/forgot-password" className="text-xs text-accent hover:underline">
                Forgot password?
              </Link>
            </div>
            <Button type="submit" variant="primary" size="md" className="w-full" disabled={busy}>
              {busy ? (
                <span className="inline-flex items-center gap-1.5">
                  <Loader2 size={13} className="animate-spin" /> Signing in…
                </span>
              ) : (
                'Sign in'
              )}
            </Button>
          </form>

          {enabledProviders.length > 0 ? (
            <>
              <div className="my-6 flex items-center gap-3 text-[11px] text-ink-subtle">
                <span className="h-px flex-1 bg-border" aria-hidden />
                or continue with
                <span className="h-px flex-1 bg-border" aria-hidden />
              </div>
              <div className="space-y-2">
                {enabledProviders.map((p) => (
                  <a
                    key={p.id}
                    href={oauthAuthorizeUrl(p.id)}
                    className="flex w-full items-center justify-center gap-2 rounded border border-border bg-surface px-3 py-2 text-sm text-ink hover:border-border-strong transition-colors"
                  >
                    Continue with {p.label}
                  </a>
                ))}
              </div>
            </>
          ) : null}

          <p className="mt-6 text-xs text-ink-muted">
            No account?{' '}
            <Link to="/register" className="text-accent hover:underline">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

function Bullet({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-2.5 text-ink-muted">
      <span className="mt-2 h-1 w-1 rounded-full bg-accent shrink-0" aria-hidden />
      <span>{children}</span>
    </li>
  )
}