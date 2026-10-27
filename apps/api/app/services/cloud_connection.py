import json
import uuid
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.adapters import get_adapter
from app.config import get_settings
from app.models.cloud_account import CloudAccount
from app.models.tenant import Tenant
from app.services.encryption import encrypt_secret

settings = get_settings()


def generate_external_id(tenant_slug: str, account_name: str) -> str:
    token = uuid.uuid4().hex[:16]
    safe_name = "".join(c for c in account_name if c.isalnum() or c in "-_")[:32]
    return f"{settings.aws_external_id_prefix}-{tenant_slug}-{safe_name}-{token}"


def build_cloudformation_url(role_name: str, external_id: str) -> str:
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": f"arn:aws:iam::{settings.aws_management_account_id}:root"},
                "Action": "sts:AssumeRole",
                "Condition": {"StringEquals": {"sts:ExternalId": external_id}},
            }
        ],
    }
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "CloudFinOps AI read-only cross-account role",
        "Resources": {
            "CloudFinOpsRole": {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "RoleName": role_name,
                    "AssumeRolePolicyDocument": trust_policy,
                    "ManagedPolicyArns": [
                        "arn:aws:iam::aws:policy/ReadOnlyAccess",
                        "arn:aws:iam::aws:policy/AWSBillingReadOnlyAccess",
                    ],
                    "MaxSessionDuration": 3600,
                    "Description": "Read-only access for CloudFinOps AI",
                },
            }
        },
        "Outputs": {
            "RoleArn": {"Value": {"Fn::GetAtt": ["CloudFinOpsRole", "Arn"]}},
        },
    }
    quick_create = {
        "templateURL": f"{settings.app_base_url}/static/cloudfinops-readonly-role.json",
        "stackName": "CloudFinOpsReadOnly",
        "param_roleName": role_name,
    }
    base = "https://console.aws.amazon.com/cloudformation/home"
    fragment = urlencode({"templateURL": quick_create["templateURL"], "stackName": quick_create["stackName"]})
    return f"{base}?region=us-east-1#/stacks/quickcreate?{fragment}"


def create_aws_account(
    db: Session,
    tenant: Tenant,
    name: str,
    account_identifier: str,
    role_arn: str,
    environment: str,
    regions: list[str],
    external_id: str | None,
) -> CloudAccount:
    ext = external_id or generate_external_id(tenant.slug, name)
    account = CloudAccount(
        tenant_id=tenant.id,
        provider="AWS",
        name=name,
        account_identifier=account_identifier,
        environment=environment,
        status="pending",
        role_arn=role_arn,
        external_id=ext,
        regions=regions,
        read_only=True,
        execution_role_configured=False,
        coverage={
            "billing": {"enabled": False, "last_sync_at": None},
            "inventory": {"enabled": False, "last_sync_at": None},
            "metrics": {"enabled": False, "last_sync_at": None},
        },
        resource_count=0,
        monthly_spend=0,
        currency="USD",
        connection_verified=False,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def create_azure_account(
    db: Session,
    tenant: Tenant,
    name: str,
    subscription_id: str,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    environment: str,
) -> CloudAccount:
    account = CloudAccount(
        tenant_id=tenant.id,
        provider="Azure",
        name=name,
        account_identifier=subscription_id,
        environment=environment,
        status="pending",
        subscription_id=subscription_id,
        tenant_external_id=tenant_id,
        client_id=client_id,
        encrypted_client_secret=encrypt_secret(client_secret),
        regions=["centralindia"],
        read_only=True,
        execution_role_configured=False,
        coverage={
            "billing": {"enabled": False, "last_sync_at": None},
            "inventory": {"enabled": False, "last_sync_at": None},
            "metrics": {"enabled": False, "last_sync_at": None},
        },
        resource_count=0,
        monthly_spend=0,
        currency="USD",
        connection_verified=False,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def verify_account(db: Session, account: CloudAccount) -> tuple[bool, str]:
    try:
        adapter = get_adapter(account.provider)
    except ValueError as exc:
        account.connection_verified = False
        account.connection_error = str(exc)
        account.status = "error"
        db.commit()
        return False, str(exc)

    ok, message = adapter.validate_connection(db, account.id)
    account.connection_verified = ok
    account.connection_error = None if ok else message
    account.status = "connected" if ok else "error"
    db.commit()
    return ok, message