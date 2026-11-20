import { API_BASE_URL, ApiError, USE_MOCKS, withMockDelay } from '@/lib/api/client'
import type { AuthSession, LoginPayload, RegisterPayload } from './types'

async function authRequest<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    let detail = 'Request failed'
    try {
      const data = await response.json()
      detail = typeof data?.detail === 'string' ? data.detail : detail
    } catch {
      // ignore
    }
    throw new ApiError(detail, response.status)
  }
  return (await response.json()) as T
}

function mockSession(email: string): AuthSession {
  return {
    accessToken: 'mock-token',
    expiresIn: 3600,
    user: {
      id: 'mock-user',
      email,
      fullName: 'Mock User',
      isSuperuser: true,
    },
    tenant: {
      id: 'mock-tenant',
      slug: 'demo',
      name: 'Demo Tenant',
      role: 'owner',
    },
  }
}

export async function register(payload: RegisterPayload): Promise<AuthSession> {
  if (USE_MOCKS) return withMockDelay(mockSession(payload.email))
  return authRequest<AuthSession>('/auth/register', payload)
}

export async function login(payload: LoginPayload): Promise<AuthSession> {
  if (USE_MOCKS) return withMockDelay(mockSession(payload.email))
  return authRequest<AuthSession>('/auth/login', payload)
}

export interface PasswordResetRequestResult {
  ok: boolean
  message: string
  resetUrl: string | null
}

export async function requestPasswordReset(email: string): Promise<PasswordResetRequestResult> {
  if (USE_MOCKS) {
    return withMockDelay({
      ok: true,
      message: 'If an account exists for that email, a reset link has been sent.',
      resetUrl: null,
    })
  }
  return authRequest<PasswordResetRequestResult>('/auth/password-reset/request', { email })
}

export async function confirmPasswordReset(token: string, password: string): Promise<{ ok: boolean; message: string }> {
  if (USE_MOCKS) {
    return withMockDelay({ ok: true, message: 'Password updated.' })
  }
  return authRequest<{ ok: boolean; message: string }>('/auth/password-reset/confirm', {
    token,
    password,
  })
}

export async function fetchMe(token: string): Promise<{ user: AuthSession['user']; tenant: AuthSession['tenant'] }> {
  if (USE_MOCKS) return withMockDelay({ user: mockSession('mock').user, tenant: mockSession('mock').tenant })
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw new ApiError('Unauthorized', response.status)
  return (await response.json()) as { user: AuthSession['user']; tenant: AuthSession['tenant'] }
}