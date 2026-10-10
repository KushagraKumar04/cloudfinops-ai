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
