import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { fetchMe } from '@/features/auth/api'
import { setStoredUser, setToken } from '@/features/auth/storage'

export function OAuthCallback() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const hash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : window.location.hash
    const params = new URLSearchParams(hash)
    const token = params.get('token')
    const err = params.get('error')

    if (err) {
      setError(err)
      return
    }
    if (!token) {
      setError('Missing authentication token')
      return
    }

    setToken(token)
    fetchMe(token)
      .then((res) => {
        setStoredUser(res.user)
        navigate('/', { replace: true })
        window.location.reload()
      })
      .catch(() => {
        setError('Could not verify the OAuth session')
      })
  }, [navigate])

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center px-4">
      <Card className="p-6 max-w-md w-full">
        {error ? (
          <div className="space-y-3">
            <h1 className="text-base font-semibold text-ink">Sign-in failed</h1>
            <p className="text-sm text-ink-muted">{error}</p>
            <a href="/login" className="inline-block text-xs text-accent hover:underline">
              Back to sign in
            </a>
          </div>
        ) : (
          <div className="flex items-center gap-3 text-sm text-ink-muted">
            <Loader2 size={14} className="animate-spin" />
            Completing sign-in…
          </div>
        )}
      </Card>
    </div>
  )
}