import { API_BASE_URL } from '@/lib/api/client'
import { request, USE_MOCKS } from '@/lib/api/client'

export interface OAuthProviderInfo {
  id: 'github' | 'google'
  label: string
  enabled: boolean
}

export async function listOAuthProviders(): Promise<OAuthProviderInfo[]> {
  if (USE_MOCKS) return []
  try {
    return await request<OAuthProviderInfo[]>('/auth/oauth/providers')
  } catch {
    return []
  }
}

export function oauthAuthorizeUrl(provider: string): string {
  return `${API_BASE_URL}/auth/oauth/${provider}/authorize`
}