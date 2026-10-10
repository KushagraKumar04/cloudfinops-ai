import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant
from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.kubernetes import (
    ClusterDetail,
    ClusterListOut,
    ClusterOut,
    CostTrendPoint,
    NamespaceOut,
    WorkloadOut,
)
from app.services.kubernetes import (
    account_name_map,
    aggregate_summary,
    cluster_counts,
    cost_trends,
    get_cluster,
    list_clusters,
    list_namespaces,
    list_workloads,
)

router = APIRouter(prefix="/kubernetes", tags=["kubernetes"])


def _to_cluster_out(
    cluster,
    account_name: str,
    counts: dict,
) -> ClusterOut:
    base = ClusterOut.model_validate(cluster)
    base.account_name = account_name
    base.namespace_count = int(counts["namespace_count"])
    base.workload_count = int(counts["workload_count"])
    base.over_provisioned_count = int(counts["over_provisioned_count"])
    base.potential_savings = round(float(counts["potential_savings"]), 2)
    return base


@router.get("/clusters", response_model=ClusterListOut)
def list_kubernetes_clusters(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ClusterListOut:
    clusters = list_clusters(db, tenant.id)
    account_names = account_name_map(db, tenant.id, {c.cloud_account_id for c in clusters})
    items: list[ClusterOut] = []
    for c in clusters:
        counts = cluster_counts(db, tenant.id, c.id)
        items.append(_to_cluster_out(c, account_names.get(c.cloud_account_id, ""), counts))
    return ClusterListOut(
        items=items,
        total=len(items),
        aggregates=aggregate_summary(clusters),
    )


@router.get("/clusters/{cluster_id}", response_model=ClusterDetail)
def get_kubernetes_cluster(
    cluster_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ClusterDetail:
    cluster = get_cluster(db, tenant.id, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    account_names = account_name_map(db, tenant.id, {cluster.cloud_account_id})
    counts = cluster_counts(db, tenant.id, cluster.id)
    cluster_out = _to_cluster_out(cluster, account_names.get(cluster.cloud_account_id, ""), counts)

    namespaces = [NamespaceOut.model_validate(n) for n in list_namespaces(db, tenant.id, cluster.id)]
    ns_names = {n.id: n.name for n in list_namespaces(db, tenant.id, cluster.id)}
    workloads: list[WorkloadOut] = []
    for w in list_workloads(db, tenant.id, cluster.id):
        item = WorkloadOut.model_validate(w)
        item.namespace_name = ns_names.get(w.namespace_id, "")
        workloads.append(item)

    return ClusterDetail(cluster=cluster_out, namespaces=namespaces, workloads=workloads)


@router.get("/clusters/{cluster_id}/namespaces", response_model=list[NamespaceOut])
def get_cluster_namespaces(
    cluster_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> list[NamespaceOut]:
    cluster = get_cluster(db, tenant.id, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return [NamespaceOut.model_validate(n) for n in list_namespaces(db, tenant.id, cluster_id)]


@router.get("/clusters/{cluster_id}/workloads", response_model=list[WorkloadOut])
def get_cluster_workloads(
    cluster_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    namespace_id: uuid.UUID | None = Query(default=None),
) -> list[WorkloadOut]:
    cluster = get_cluster(db, tenant.id, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    ns_names = {n.id: n.name for n in list_namespaces(db, tenant.id, cluster_id)}
    out: list[WorkloadOut] = []
    for w in list_workloads(db, tenant.id, cluster_id, namespace_id):
        item = WorkloadOut.model_validate(w)
        item.namespace_name = ns_names.get(w.namespace_id, "")
        out.append(item)
    return out


@router.get("/clusters/{cluster_id}/trends", response_model=list[CostTrendPoint])
def get_cluster_trends(
    cluster_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    days: int = Query(default=30, ge=7, le=180),
) -> list[CostTrendPoint]:
    cluster = get_cluster(db, tenant.id, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    rows = cost_trends(db, tenant.id, cluster_id, days)
    return [CostTrendPoint(**r) for r in rows]