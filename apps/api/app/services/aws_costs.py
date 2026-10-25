import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger("app.aws.costs")

BOTO_CONFIG = Config(retries={"max_attempts": 4, "mode": "adaptive"}, connect_timeout=10, read_timeout=60)


def fetch_costs(session, start: date, end: date) -> list[dict[str, Any]]:
    try:
        ce = session.client("ce", region_name="us-east-1", config=BOTO_CONFIG)
    except (ClientError, BotoCoreError) as exc:
        logger.warning("Cost Explorer client creation failed: %s", exc)
        return []

    out: list[dict[str, Any]] = []
    next_token: str | None = None
    pages = 0
    max_pages = 40

    while pages < max_pages:
        pages += 1
        params = {
            "TimePeriod": {
                "Start": start.isoformat(),
                "End": (end + timedelta(days=1)).isoformat(),
            },
            "Granularity": "DAILY",
            "Metrics": ["UnblendedCost"],
            "GroupBy": [
                {"Type": "DIMENSION", "Key": "SERVICE"},
                {"Type": "DIMENSION", "Key": "REGION"},
            ],
        }
        if next_token:
            params["NextPageToken"] = next_token

        try:
            response = ce.get_cost_and_usage(**params)
        except (ClientError, BotoCoreError) as exc:
            logger.warning("Cost Explorer request failed: %s", exc)
            break

        for bucket in response.get("ResultsByTime", []):
            bucket_date = bucket["TimePeriod"]["Start"]
            for group in bucket.get("Groups", []):
                keys = group.get("Keys", [])
                metric = group.get("Metrics", {}).get("UnblendedCost", {})
                amount = Decimal(metric.get("Amount", "0"))
                if amount <= 0:
                    continue
                service = keys[0] if len(keys) > 0 else "Unknown"
                region = keys[1] if len(keys) > 1 else "global"
                out.append(
                    {
                        "date": bucket_date,
                        "service": service,
                        "region": region,
                        "resource_id": None,
                        "cost": float(amount),
                        "currency": metric.get("Unit", "USD"),
                        "usage_quantity": 0.0,
                        "usage_unit": "",
                    }
                )

        next_token = response.get("NextPageToken")
        if not next_token:
            break

    return out