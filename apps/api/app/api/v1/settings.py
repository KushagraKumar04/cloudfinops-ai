from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant, require_permission
from app.services.permissions import Permission
from app.config import get_settings
from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.settings import (
    LlmConfig,
    LlmIn,
    PoliciesIn,
    PolicyRule,
    SettingsOut,
    ThresholdRule,
    ThresholdsIn,
)

settings = get_settings()

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_SETTINGS = {
    "policies": [],
    "thresholds": [],
    "llm": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "maxTokens": 2048,
        "cacheEnabled": True,
        "compactToolOutputs": True,
        "promptVersion": "2026-09-01",
    },
}


def _read(tenant: Tenant) -> SettingsOut:
    data = tenant.settings or DEFAULT_SETTINGS
    llm_data = dict(data.get("llm", DEFAULT_SETTINGS["llm"]))
    llm_data["api_key_configured"] = bool(settings.llm_api_key)
    return SettingsOut(
        policies=[PolicyRule(**p) for p in data.get("policies", [])],
        thresholds=[ThresholdRule(**t) for t in data.get("thresholds", [])],
        llm=LlmConfig(**llm_data),
    )


@router.get("", response_model=SettingsOut)
def get_settings(
    tenant: Tenant = Depends(get_current_tenant),
) -> SettingsOut:
    return _read(tenant)


@router.put(
    "/policies",
    response_model=list[PolicyRule],
    dependencies=[Depends(require_permission(Permission.EDIT_SETTINGS))],
)
def update_policies(
    payload: PoliciesIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> list[PolicyRule]:
    data = dict(tenant.settings or DEFAULT_SETTINGS)
    data["policies"] = [p.model_dump(by_alias=True) for p in payload.policies]
    tenant.settings = data
    db.commit()
    return payload.policies


@router.put(
    "/thresholds",
    response_model=list[ThresholdRule],
    dependencies=[Depends(require_permission(Permission.EDIT_SETTINGS))],
)
def update_thresholds(
    payload: ThresholdsIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> list[ThresholdRule]:
    data = dict(tenant.settings or DEFAULT_SETTINGS)
    data["thresholds"] = [t.model_dump(by_alias=True) for t in payload.thresholds]
    tenant.settings = data
    db.commit()
    return payload.thresholds


@router.put(
    "/llm",
    response_model=LlmConfig,
    dependencies=[Depends(require_permission(Permission.EDIT_SETTINGS))],
)
def update_llm(
    payload: LlmIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> LlmConfig:
    data = dict(tenant.settings or DEFAULT_SETTINGS)
    data["llm"] = payload.llm.model_dump(by_alias=True)
    tenant.settings = data
    db.commit()
    return payload.llm