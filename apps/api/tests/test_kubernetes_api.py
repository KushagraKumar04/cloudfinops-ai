import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.models.kubernetes import (
    KubernetesCluster,
    KubernetesCostAllocation,
    KubernetesNamespace,
    KubernetesWorkload,
)


def _seed_k8s(db_session, tenant, account_id):
    cluster_id = uuid.uuid4()
    cluster = KubernetesCluster(
        id=cluster_id,
        tenant_id=tenant.id,
        cloud_account_id=account_id,
        provider="AWS",
        name="test-eks",
        version="1.30",
        region="us-east-1",
        status="active",
        node_count=3,
        total_cpu_cores=Decimal("24"),
        total_memory_gb=Decimal("96"),
        monthly_cost=Decimal("900"),
    )
    db_session.add(cluster)
    db_session.flush()

    namespace = KubernetesNamespace(
        tenant_id=tenant.id,
        cluster_id=cluster.id,
        name="default",
        cpu_request_cores=Decimal("8"),
        cpu_limit_cores=Decimal("12"),
        cpu_usage_avg_cores=Decimal("2"),
        memory_request_gb=Decimal("32"),
        memory_limit_gb=Decimal("48"),
        memory_usage_avg_gb=Decimal("10"),
        monthly_cost=Decimal("500"),
    )
    db_session.add(namespace)
    db_session.flush()

    workload = KubernetesWorkload(
        tenant_id=tenant.id,
        cluster_id=cluster.id,
        namespace_id=namespace.id,
        name="api",
        kind="Deployment",
        replicas=3,
        cpu_request_cores=Decimal("6"),
        cpu_limit_cores=Decimal("12"),
        cpu_usage_avg_cores=Decimal("1.5"),
        memory_request_gb=Decimal("24"),
        memory_limit_gb=Decimal("48"),
        memory_usage_avg_gb=Decimal("6"),
        monthly_cost=Decimal("300"),
        potential_savings=Decimal("80"),
        over_provisioned=True,
    )
    db_session.add(workload)

    today = date.today()
    for i in range(30):
        d = today - timedelta(days=i)
        db_session.add(
            KubernetesCostAllocation(
                tenant_id=tenant.id,
                cluster_id=cluster.id,
                namespace_id=namespace.id,
                workload_id=None,
                date=d,
                cost=Decimal("16.67"),
                cpu_cost=Decimal("9.17"),
                memory_cost=Decimal("5.00"),
                storage_cost=Decimal("1.67"),
                network_cost=Decimal("0.83"),
            )
        )
    db_session.commit()
    return cluster_id


def test_list_clusters_empty(client, seeded_tenant):
    r = client.get("/api/v1/kubernetes/clusters")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["aggregates"]["cluster_count"] == 0


def test_list_clusters(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_k8s(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/kubernetes/clusters")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["name"] == "test-eks"
    assert item["namespaceCount"] == 1
    assert item["workloadCount"] == 1
    assert item["overProvisionedCount"] == 1
    assert item["potentialSavings"] == 80.0
    assert body["aggregates"]["total_monthly_cost"] == 900.0


def test_get_cluster_detail(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    cluster_id = _seed_k8s(db_session, seeded_tenant, account.id)

    r = client.get(f"/api/v1/kubernetes/clusters/{cluster_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["cluster"]["name"] == "test-eks"
    assert len(body["namespaces"]) == 1
    assert len(body["workloads"]) == 1
    assert body["workloads"][0]["namespaceName"] == "default"
    assert body["workloads"][0]["overProvisioned"] is True


def test_get_cluster_namespaces(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    cluster_id = _seed_k8s(db_session, seeded_tenant, account.id)

    r = client.get(f"/api/v1/kubernetes/clusters/{cluster_id}/namespaces")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "default"


def test_get_cluster_workloads(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    cluster_id = _seed_k8s(db_session, seeded_tenant, account.id)

    r = client.get(f"/api/v1/kubernetes/clusters/{cluster_id}/workloads")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_get_cluster_trends(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    cluster_id = _seed_k8s(db_session, seeded_tenant, account.id)

    r = client.get(f"/api/v1/kubernetes/clusters/{cluster_id}/trends?days=30")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 30
    assert body[0]["cost"] > 0


def test_get_cluster_404(client, seeded_tenant):
    r = client.get(f"/api/v1/kubernetes/clusters/{uuid.uuid4()}")
    assert r.status_code == 404