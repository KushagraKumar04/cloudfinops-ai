const TOKEN_KEY = 'cloudfinops.token'
const USER_KEY = 'cloudfinops.user'

export interface StoredUser {
  id: string
  email: string
  fullName: string
  isSuperuser: boolean
}

export interface StoredTenant {
  id: string
  slug: string
  name: string
  role: string
}

export function getToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token)
  } catch {
    // ignore
  }
}

export function clearToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY)
    window.localStorage.removeItem(USER_KEY)
  } catch {
    // ignore
  }
}

export function getStoredUser(): StoredUser | null {
  try {
    const raw = window.localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as StoredUser) : null
  } catch {
    return null
  }
}

export function setStoredUser(user: StoredUser | null): void {
  try {
    if (user) {
      window.localStorage.setItem(USER_KEY, JSON.stringify(user))
    } else {
      window.localStorage.removeItem(USER_KEY)
    }
  } catch {
    // ignore
  }
}