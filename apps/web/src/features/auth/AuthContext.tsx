import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { USE_MOCKS } from '@/lib/api/client'
import { fetchMe, login as apiLogin, register as apiRegister } from './api'
import {
  clearToken,
  getStoredUser,
  getToken,
  setStoredUser,
  setToken,
  type StoredTenant,
  type StoredUser,
} from './storage'
import { roleHasPermission, type Permission } from './permissions'
import type { LoginPayload, RegisterPayload } from './types'

export interface AuthContextValue {
  user: StoredUser | null
  tenant: StoredTenant | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (payload: LoginPayload) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  logout: () => void
  can: (permission: Permission) => boolean
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<StoredUser | null>(() => (USE_MOCKS ? { id: 'mock', email: 'mock@local', fullName: 'Mock User', isSuperuser: true } : getStoredUser()))
  const [tenant, setTenant] = useState<StoredTenant | null>(() => (USE_MOCKS ? { id: 'mock', slug: 'demo', name: 'Demo Tenant', role: 'owner' } : null))
  const [isLoading, setIsLoading] = useState<boolean>(() => !USE_MOCKS && !getStoredUser())

  useEffect(() => {
    if (USE_MOCKS) {
      setIsLoading(false)
      return
    }
    const token = getToken()
    if (!token) {
      setIsLoading(false)
      return
    }
    let cancelled = false
    fetchMe(token)
      .then((res) => {
        if (cancelled) return
        setUser(res.user)
        setTenant(res.tenant)
        setStoredUser(res.user)
      })
      .catch(() => {
        if (cancelled) return
        clearToken()
        setUser(null)
        setTenant(null)
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const handler = () => {
      setUser(null)
      setTenant(null)
      setStoredUser(null)
    }
    window.addEventListener('cloudfinops:unauthorized', handler)
    return () => window.removeEventListener('cloudfinops:unauthorized', handler)
  }, [])

  const login = useCallback(async (payload: LoginPayload) => {
    const session = await apiLogin(payload)
    setToken(session.accessToken)
    setStoredUser(session.user)
    setUser(session.user)
    setTenant(session.tenant)
  }, [])

  const register = useCallback(async (payload: RegisterPayload) => {
    const session = await apiRegister(payload)
    setToken(session.accessToken)
    setStoredUser(session.user)
    setUser(session.user)
    setTenant(session.tenant)
  }, [])

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
    setTenant(null)
    if (USE_MOCKS) {
      setUser({ id: 'mock', email: 'mock@local', fullName: 'Mock User', isSuperuser: true })
      setTenant({ id: 'mock', slug: 'demo', name: 'Demo Tenant', role: 'owner' })
    }
  }, [])

  const can = useCallback(
    (permission: Permission) => roleHasPermission(tenant?.role, permission),
    [tenant],
  )

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      tenant,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      register,
      logout,
      can,
    }),
    [user, tenant, isLoading, login, register, logout, can],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}