import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, ExternalLink } from 'lucide-react'
import { useAuth } from '@/features/auth/useAuth'

interface LegalSection {
  title: string
  body: string
}

export function LegalLayout({
  title,
  intro,
  sections,
  footer,
}: {
  title: string
  intro: string
  sections: LegalSection[]
  footer: string
}) {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  const fallbackHref = isAuthenticated ? '/' : '/register'
  const fallbackLabel = isAuthenticated ? 'Back to app' : 'Back to sign up'

  return (
    <div className="min-h-screen bg-canvas flex flex-col">
      <header className="sticky top-0 z-10 border-b border-border bg-canvas/95 backdrop-blur-sm">
        <div className="mx-auto max-w-3xl px-6 h-14 flex items-center justify-between gap-4">
          <Link to={fallbackHref} className="flex items-center gap-2 shrink-0">
            <span className="h-6 w-6 rounded-sm bg-accent" aria-hidden />
            <span className="text-sm font-semibold tracking-tight text-ink">CloudFinOps AI</span>
          </Link>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="inline-flex items-center gap-1.5 rounded px-2 py-1 text-xs text-ink-muted hover:text-ink hover:bg-surface-muted transition-colors"
              aria-label="Go back"
            >
              <ArrowLeft size={13} />
              Back
            </button>
            <Link
              to={fallbackHref}
              className="hidden sm:inline-flex items-center gap-1.5 rounded px-2 py-1 text-xs font-medium text-accent hover:bg-accent-soft transition-colors"
            >
              {fallbackLabel}
              <ExternalLink size={11} />
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <div className="mx-auto max-w-3xl px-6 py-12">
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center rounded-sm border border-warning-soft bg-warning-soft px-2 py-0.5 text-[11px] font-medium text-warning">
              Draft
            </span>
            <span className="text-[11px] text-ink-subtle">
              Not legal advice. Review with counsel before publishing.
            </span>
          </div>

          <h1 className="mt-4 text-2xl font-semibold text-ink tracking-tight">{title}</h1>
          <p className="mt-2 text-sm text-ink-muted leading-relaxed max-w-2xl">{intro}</p>

          <ol className="mt-10 space-y-8">
            {sections.map((section, i) => (
              <li key={section.title}>
                <div className="flex items-baseline gap-3">
                  <span className="text-[11px] font-mono text-ink-subtle tabular-nums w-5 shrink-0">
                    {(i + 1).toString().padStart(2, '0')}
                  </span>
                  <h2 className="text-base font-semibold text-ink tracking-tight">
                    {section.title}
                  </h2>
                </div>
                <p className="mt-2 ml-8 text-sm text-ink-muted leading-relaxed">
                  {section.body}
                </p>
              </li>
            ))}
          </ol>

          <div className="mt-12 rounded-md border border-border bg-surface-muted/40 px-4 py-3">
            <p className="text-xs text-ink-muted leading-relaxed">{footer}</p>
          </div>
        </div>
      </main>

      <footer className="border-t border-border bg-canvas">
        <div className="mx-auto max-w-3xl px-6 py-5 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-ink-subtle">
          <span>CloudFinOps AI · v0.1</span>
          <div className="flex items-center gap-3">
            <Link to="/terms" className="hover:text-ink transition-colors">
              Terms
            </Link>
            <span aria-hidden>·</span>
            <Link to="/privacy" className="hover:text-ink transition-colors">
              Privacy
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}