import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cloud_account import CloudAccount
from app.models.kubernetes import (
    KubernetesCluster,
    KubernetesCostAllocation,
    KubernetesNamespace,
    KubernetesWorkload,
)


def list_clusters(db: Session, tenant_id: uuid.UUID) -> list[KubernetesCluster]:
    stmt = (
        select(KubernetesCluster)
        .where(KubernetesCluster.tenant_id == tenant_id)
        .order_by(KubernetesCluster.monthly_cost.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_cluster(
    db: Session, tenant_id: uuid.UUID, cluster_id: uuid.UUID
) -> KubernetesCluster | None:
    stmt = select(KubernetesCluster).where(
        KubernetesCluster.id == cluster_id,
        KubernetesCluster.tenant_id == tenant_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def list_namespaces(
    db: Session, tenant_id: uuid.UUID, cluster_id: uuid.UUID
) -> list[KubernetesNamespace]:
    stmt = (
        select(KubernetesNamespace)
        .where(
            KubernetesNamespace.tenant_id == tenant_id,
            KubernetesNamespace.cluster_id == cluster_id,
        )
        .order_by(KubernetesNamespace.monthly_cost.desc())
    )
    return list(db.execute(stmt).scalars().all())


def list_workloads(
    db: Session,
    tenant_id: uuid.UUID,
    cluster_id: uuid.UUID,
    namespace_id: uuid.UUID | None = None,
) -> list[KubernetesWorkload]:
    stmt = select(KubernetesWorkload).where(
        KubernetesWorkload.tenant_id == tenant_id,
        KubernetesWorkload.cluster_id == cluster_id,
    )
    if namespace_id is not None:
        stmt = stmt.where(KubernetesWorkload.namespace_id == namespace_id)
    stmt = stmt.order_by(KubernetesWorkload.monthly_cost.desc())
    return list(db.execute(stmt).scalars().all())


def cluster_counts(
    db: Session, tenant_id: uuid.UUID, cluster_id: uuid.UUID
) -> dict[str, int | float]:
    ns_stmt = select(func.count(KubernetesNamespace.id)).where(
        KubernetesNamespace.tenant_id == tenant_id,
        KubernetesNamespace.cluster_id == cluster_id,
    )
    wl_stmt = select(func.count(KubernetesWorkload.id)).where(
        KubernetesWorkload.tenant_id == tenant_id,
        KubernetesWorkload.cluster_id == cluster_id,
    )
    over_stmt = select(func.count(KubernetesWorkload.id)).where(
        KubernetesWorkload.tenant_id == tenant_id,
        KubernetesWorkload.cluster_id == cluster_id,
        KubernetesWorkload.over_provisioned.is_(True),
    )
    savings_stmt = select(func.coalesce(func.sum(KubernetesWorkload.potential_savings), 0)).where(
        KubernetesWorkload.tenant_id == tenant_id,
        KubernetesWorkload.cluster_id == cluster_id,
    )

    return {
        "namespace_count": int(db.execute(ns_stmt).scalar() or 0),
        "workload_count": int(db.execute(wl_stmt).scalar() or 0),
        "over_provisioned_count": int(db.execute(over_stmt).scalar() or 0),
        "potential_savings": float(db.execute(savings_stmt).scalar() or 0),
    }


def cost_trends(
    db: Session,
    tenant_id: uuid.UUID,
    cluster_id: uuid.UUID,
    days: int = 30,
) -> list[dict[str, object]]:
    start = date.today() - timedelta(days=days - 1)
    stmt = (
        select(
            KubernetesCostAllocation.date,
            func.coalesce(func.sum(KubernetesCostAllocation.cost), 0),
            func.coalesce(func.sum(KubernetesCostAllocation.cpu_cost), 0),
            func.coalesce(func.sum(KubernetesCostAllocation.memory_cost), 0),
            func.coalesce(func.sum(KubernetesCostAllocation.storage_cost), 0),
            func.coalesce(func.sum(KubernetesCostAllocation.network_cost), 0),
        )
        .where(
            KubernetesCostAllocation.tenant_id == tenant_id,
            KubernetesCostAllocation.cluster_id == cluster_id,
            KubernetesCostAllocation.date >= start,
        )
        .group_by(KubernetesCostAllocation.date)
        .order_by(KubernetesCostAllocation.date.asc())
    )
    return [
        {
            "date": row[0],
            "cost": float(row[1] or 0),
            "cpu_cost": float(row[2] or 0),
            "memory_cost": float(row[3] or 0),
            "storage_cost": float(row[4] or 0),
            "network_cost": float(row[5] or 0),
        }
        for row in db.execute(stmt).all()
    ]


def account_name_map(
    db: Session, tenant_id: uuid.UUID, account_ids: set[uuid.UUID]
) -> dict[uuid.UUID, str]:
    if not account_ids:
        return {}
    stmt = select(CloudAccount).where(
        CloudAccount.tenant_id == tenant_id,
        CloudAccount.id.in_(account_ids),
    )
    return {a.id: a.name for a in db.execute(stmt).scalars().all()}


def aggregate_summary(clusters: list[KubernetesCluster]) -> dict[str, float | int]:
    total_cost = sum(float(c.monthly_cost) for c in clusters)
    total_nodes = sum(c.node_count for c in clusters)
    total_cpu = sum(float(c.total_cpu_cores) for c in clusters)
    total_memory = sum(float(c.total_memory_gb) for c in clusters)
    return {
        "cluster_count": len(clusters),
        "node_count": total_nodes,
        "total_cpu_cores": round(total_cpu, 2),
        "total_memory_gb": round(total_memory, 2),
        "total_monthly_cost": round(total_cost, 2),
    }