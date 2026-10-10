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


