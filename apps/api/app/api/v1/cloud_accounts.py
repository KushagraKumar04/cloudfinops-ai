import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant
from app.config import get_settings
from app.db.session import get_db
from app.models.cloud_account import CloudAccount
from app.models.tenant import Tenant
from app.schemas.cloud_account import CloudAccountOut, SyncResponse, ValidateResponse
from app.schemas.cloud_connection import (
    AwsConnectIn,
    AwsConnectOut,
    AzureConnectIn,
    AzureConnectOut,
    VerifyOut,
)
from app.services.cloud_connection import (
    build_cloudformation_url,
    create_aws_account,
    create_azure_account,
    verify_account,
)

from app.services.ingestion import IngestionService

router = APIRouter(prefix="/cloud/accounts", tags=["cloud-accounts"])
settings = get_settings()


@router.get("", response_model=list[CloudAccountOut])
def list_cloud_accounts(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> list[CloudAccount]:
    stmt = (
        select(CloudAccount)
        .where(CloudAccount.tenant_id == tenant.id)
        .order_by(CloudAccount.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


@router.post("/aws", response_model=AwsConnectOut)
def connect_aws(
    payload: AwsConnectIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> AwsConnectOut:
    account = create_aws_account(
        db=db,
        tenant=tenant,
        name=payload.name,
        account_identifier=payload.account_identifier,
        role_arn=payload.role_arn,
        environment=payload.environment,
        regions=payload.regions,
        external_id=payload.external_id,
    )
    role_name = payload.role_arn.split("/")[-1] if "/" in payload.role_arn else "CloudFinOpsReadOnly"
    cf_url = build_cloudformation_url(role_name, account.external_id or "")
    return AwsConnectOut(
        id=str(account.id),
        external_id=account.external_id or "",
        role_arn=payload.role_arn,
        cloudformation_url=cf_url,
        trust_policy={
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": f"arn:aws:iam::{settings.aws_management_account_id}:root"},
                    "Action": "sts:AssumeRole",
                    "Condition": {"StringEquals": {"sts:ExternalId": account.external_id}},
                }
            ],
        },
        note="Create the IAM role in your AWS account with the trust policy shown. Then click Verify connection.",
    )


@router.post("/azure", response_model=AzureConnectOut)
def connect_azure(
    payload: AzureConnectIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> AzureConnectOut:
    account = create_azure_account(
        db=db,
        tenant=tenant,
        name=payload.name,
        subscription_id=payload.subscription_id,
        tenant_id=payload.tenant_id,
        client_id=payload.client_id,
        client_secret=payload.client_secret,
        environment=payload.environment,
    )
    az_cmd = (
        f'az role assignment create --assignee "{payload.client_id}" '
        f'--role "Cost Management Reader" '
        f"--scope /subscriptions/{payload.subscription_id}"
    )
    return AzureConnectOut(
        id=str(account.id),
        subscription_id=payload.subscription_id,
        az_cli_command=az_cmd,
        note="Run the command in Azure CLI to grant Cost Management Reader at the subscription scope.",
    )


@router.post("/{account_id}/verify", response_model=VerifyOut)
def verify(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> VerifyOut:
    account = db.get(CloudAccount, account_id)
    if account is None or account.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Cloud account not found")
    ok, message = verify_account(db, account)
    return VerifyOut(ok=ok, message=message, account_id=str(account.id))


@router.post("/{account_id}/sync", response_model=SyncResponse)
def sync_cloud_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> SyncResponse:
    account = db.get(CloudAccount, account_id)
    if account is None or account.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Cloud account not found")
    if not account.connection_verified and not settings.mock_adapters:
        raise HTTPException(status_code=409, detail="Verify the connection before syncing")

    account.status = "syncing"
    db.commit()

    service = IngestionService(db)
    service.sync_account(account.id)

    return SyncResponse(id=account.id, status="started")


@router.post("/{account_id}/validate", response_model=ValidateResponse)
def validate_cloud_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ValidateResponse:
    account = db.get(CloudAccount, account_id)
    if account is None or account.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Cloud account not found")
    ok, message = verify_account(db, account)
    return ValidateResponse(id=account.id, ok=ok, message=message)


@router.delete("/{account_id}", status_code=204)
def delete_cloud_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    account = db.get(CloudAccount, account_id)
    if account is None or account.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Cloud account not found")
    db.delete(account)
    db.commit()
    return None


@router.get("/{account_id}/setup-preview")
def setup_preview(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> dict:
    account = db.get(CloudAccount, account_id)
    if account is None or account.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Cloud account not found")
    if account.provider == "AWS":
        role_name = account.role_arn.split("/")[-1] if account.role_arn else "CloudFinOpsReadOnly"
        return {
            "provider": "AWS",
            "externalId": account.external_id,
            "roleName": role_name,
            "trustPolicy": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": f"arn:aws:iam::{settings.aws_management_account_id}:root"},
                        "Action": "sts:AssumeRole",
                        "Condition": {"StringEquals": {"sts:ExternalId": account.external_id}},
                    }
                ],
            },
            "managedPolicies": [
                "arn:aws:iam::aws:policy/ReadOnlyAccess",
                "arn:aws:iam::aws:policy/AWSBillingReadOnlyAccess",
            ],
        }
    return {
        "provider": "Azure",
        "subscriptionId": account.subscription_id,
        "clientId": account.client_id,
        "tenantId": account.tenant_external_id,
        "azCommand": (
            f'az role assignment create --assignee "{account.client_id}" '
            f'--role "Cost Management Reader" '
            f"--scope /subscriptions/{account.subscription_id}"
        ),
    }