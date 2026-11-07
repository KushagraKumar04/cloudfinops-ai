def test_list_cloud_accounts_empty(client):
    r = client.get("/api/v1/cloud/accounts")
    assert r.status_code == 200
    assert r.json() == []


def test_list_cloud_accounts_with_seed(client, seeded_tenant):
    r = client.get("/api/v1/cloud/accounts")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    providers = {a["provider"] for a in body}
    assert providers == {"AWS", "Azure"}

    aws = next(a for a in body if a["provider"] == "AWS")
    assert aws["identifier"] == "123456789012"
    assert aws["roleArn"].endswith("CloudFinOpsReadOnly")
    assert aws["readOnly"] is True
    assert aws["resourceCount"] == 812
    assert aws["monthlySpend"] == 98200.0

    azure = next(a for a in body if a["provider"] == "Azure")
    assert azure["subscriptionId"] == "9f2c-1a4e-8b7d-2c1f"
    assert azure["tenantId"] == "acme.onmicrosoft.com"


def test_sync_cloud_account(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    r = client.post(f"/api/v1/cloud/accounts/{account.id}/sync")
    assert r.status_code == 200
    assert r.json()["status"] == "started"


def test_sync_unknown_account(client, seeded_tenant):
    r = client.post("/api/v1/cloud/accounts/00000000-0000-0000-0000-000000000000/sync")
    assert r.status_code == 404


def test_validate_cloud_account(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    r = client.post(f"/api/v1/cloud/accounts/{account.id}/validate")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True