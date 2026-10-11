import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant, get_current_user, require_permission
from app.services.permissions import Permission
from app.db.session import get_db
from app.models.audit import AuditEvent
from app.models.commitment import CommitmentRecommendation
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.commitment import (
    CommitmentApprovalOut,
    CommitmentDecisionIn,
    CommitmentListOut,
    CommitmentOut,
    CommitmentRecommendationList,
    CommitmentRecommendationOut,
    CoverageSummary,
)
from app.services.commitments import (
    account_name_map,
    apply_decision,
    coverage_snapshot,
    get_recommendation,
    list_commitments,
    list_recommendations,
)

router = APIRouter(prefix="/commitments", tags=["commitments"])
