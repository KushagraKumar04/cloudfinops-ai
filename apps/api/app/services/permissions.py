from enum import Enum


class Permission(str, Enum):
    VIEW = "view"
    APPROVE_RECOMMENDATION = "approve_recommendation"
    EXECUTE = "execute"
    MANAGE_CLOUD_ACCOUNTS = "manage_cloud_accounts"
    SYNC_CLOUD_ACCOUNTS = "sync_cloud_accounts"
    EDIT_SETTINGS = "edit_settings"
    MANAGE_NOTIFICATIONS = "manage_notifications"
    MANAGE_COMMITMENTS = "manage_commitments"
    MANAGE_TEAM = "manage_team"


ROLE_ORDER: dict[str, int] = {
    "viewer": 0,
    "member": 1,
    "admin": 2,
    "owner": 3,
}


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "viewer": {Permission.VIEW},
    "member": {
        Permission.VIEW,
        Permission.APPROVE_RECOMMENDATION,
        Permission.SYNC_CLOUD_ACCOUNTS,
    },
    "admin": {
        Permission.VIEW,
        Permission.APPROVE_RECOMMENDATION,
        Permission.EXECUTE,
        Permission.MANAGE_CLOUD_ACCOUNTS,
        Permission.SYNC_CLOUD_ACCOUNTS,
        Permission.EDIT_SETTINGS,
        Permission.MANAGE_NOTIFICATIONS,
        Permission.MANAGE_COMMITMENTS,
    },
    "owner": {
        Permission.VIEW,
        Permission.APPROVE_RECOMMENDATION,
        Permission.EXECUTE,
        Permission.MANAGE_CLOUD_ACCOUNTS,
        Permission.SYNC_CLOUD_ACCOUNTS,
        Permission.EDIT_SETTINGS,
        Permission.MANAGE_NOTIFICATIONS,
        Permission.MANAGE_COMMITMENTS,
        Permission.MANAGE_TEAM,
    },
}


VALID_ROLES = set(ROLE_PERMISSIONS.keys())


def has_permission(role: str, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


def permissions_for_role(role: str) -> list[str]:
    return sorted(p.value for p in ROLE_PERMISSIONS.get(role, set()))