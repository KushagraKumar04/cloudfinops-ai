from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.models.tenant import Tenant

settings = get_settings()


def get_current_tenant(db: Session = Depends(get_db)) -> Tenant:
    stmt = select(Tenant).where(Tenant.slug == settings.default_tenant_slug).limit(1)
    tenant = db.execute(stmt).scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(slug=settings.default_tenant_slug, name="Demo Tenant")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    return tenant


DatabaseDep = Depends(get_db)
TenantDep = Depends(get_current_tenant)


__all__ = ["DatabaseDep", "TenantDep", "Iterator"]