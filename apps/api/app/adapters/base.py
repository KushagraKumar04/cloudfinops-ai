import uuid
from datetime import date
from typing import Any, Protocol

from sqlalchemy.orm import Session


class CloudProviderAdapter(Protocol):
    provider: str

    def validate_connection(self, db: Session, cloud_account_id: uuid.UUID) -> tuple[bool, str]: ...

    def get_resources(self, db: Session, cloud_account_id: uuid.UUID) -> list[dict[str, Any]]: ...

    def get_costs(
        self,
        db: Session,
        cloud_account_id: uuid.UUID,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]: ...

    def get_metrics(
        self,
        db: Session,
        resource_ids: list[uuid.UUID],
        start: date,
        end: date,
    ) -> list[dict[str, Any]]: ...

    def get_prices(
        self,
        resource_type: str,
        region: str,
    ) -> list[dict[str, Any]]: ...