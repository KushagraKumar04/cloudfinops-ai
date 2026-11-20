export type Permission =
  | 'view'
  | 'approve_recommendation'
  | 'execute'
  | 'manage_cloud_accounts'
  | 'sync_cloud_accounts'
  | 'edit_settings'
  | 'manage_notifications'
  | 'manage_commitments'
  | 'manage_team'

export type Role = 'owner' | 'admin' | 'member' | 'viewer'

export const ROLE_PERMISSIONS: Record<Role, Set<Permission>> = {
  owner: new Set<Permission>([
    'view',
    'approve_recommendation',
    'execute',
    'manage_cloud_accounts',
    'sync_cloud_accounts',
    'edit_settings',
    'manage_notifications',
    'manage_commitments',
    'manage_team',
  ]),
  admin: new Set<Permission>([
    'view',
    'approve_recommendation',
    'execute',
    'manage_cloud_accounts',
    'sync_cloud_accounts',
    'edit_settings',
    'manage_notifications',
    'manage_commitments',
  ]),
  member: new Set<Permission>([
    'view',
    'approve_recommendation',
    'sync_cloud_accounts',
  ]),
  viewer: new Set<Permission>(['view']),
}

export function roleHasPermission(role: string | null | undefined, permission: Permission): boolean {
  if (!role) return false
  const set = ROLE_PERMISSIONS[role as Role]
  return set ? set.has(permission) : false
}

export const ROLE_LABEL: Record<Role, string> = {
  owner: 'Owner',
  admin: 'Admin',
  member: 'Member',
  viewer: 'Viewer',
}