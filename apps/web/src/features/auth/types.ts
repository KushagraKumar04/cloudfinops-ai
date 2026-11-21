import type { StoredTenant, StoredUser } from './storage'

export interface AuthSession {
  accessToken: string
  expiresIn: number
  user: StoredUser
  tenant: StoredTenant | null
}

export interface RegisterPayload {
  email: string
  password: string
  fullName?: string
  organizationName?: string
}

export interface LoginPayload {
  email: string
  password: string
}