from app.adapters import AWSAdapter, AzureAdapter, get_adapter


def test_get_adapter_aws():
    adapter = get_adapter("AWS")
    assert isinstance(adapter, AWSAdapter)


def test_get_adapter_azure():
    adapter = get_adapter("azure")
    assert isinstance(adapter, AzureAdapter)


def test_get_adapter_unknown():
    try:
        get_adapter("gcp")
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_aws_validate_connection(db_session, seeded_tenant):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(
        select(CloudAccount).where(CloudAccount.provider == "AWS")
    ).scalars().first()
    adapter = AWSAdapter()
    ok, message = adapter.validate_connection(db_session, account.id)
    assert ok is True
    assert "validated" in message.lower()


def test_azure_validate_connection(db_session, seeded_tenant):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(
        select(CloudAccount).where(CloudAccount.provider == "Azure")
    ).scalars().first()
    adapter = AzureAdapter()
    ok, message = adapter.validate_connection(db_session, account.id)
    assert ok is True


def test_ingestion_sync_account(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from app.models.resource import Resource
    from app.services.ingestion import IngestionService
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()

    db_session.add(
        Resource(
            tenant_id=seeded_tenant.id,
            cloud_account_id=account.id,
            provider="AWS",
            cloud_id="i-sync-test",
            name="sync-test",
            type="EC2 m5.large",
            service="EC2",
            region="us-east-1",
            environment="production",
            status="running",
        )
    )
    db_session.commit()

    service = IngestionService(db_session)
    result = service.sync_account(account.id)
    assert result.resources_fetched >= 1
    assert result.errors == []