import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger("app.aws.metrics")

BOTO_CONFIG = Config(retries={"max_attempts": 4, "mode": "adaptive"}, connect_timeout=10, read_timeout=30)


def _series_from_datapoints(datapoints: list[dict[str, Any]], days: int) -> list[float]:
    by_day: dict[date, float] = {}
    for dp in datapoints:
        ts = dp.get("Timestamp")
        value = dp.get("Average")
        if ts is None or value is None:
            continue
        day = ts.date() if isinstance(ts, datetime) else ts
        by_day[day] = float(value)

    today = date.today()
    out: list[float] = []
    for offset in range(days - 1, -1, -1):
        d = today - timedelta(days=offset)
        out.append(round(by_day.get(d, 0.0), 2))
    return out


def _fetch_metric(
    client,
    namespace: str,
    metric_name: str,
    dimensions: list[dict[str, str]],
    days: int,
    stat: str = "Average",
) -> list[float]:
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    try:
        response = client.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start,
            EndTime=end,
            Period=86400,
            Statistics=[stat],
        )
    except (ClientError, BotoCoreError) as exc:
        logger.debug("Metric %s/%s failed: %s", namespace, metric_name, exc)
        return []
    return _series_from_datapoints(response.get("Datapoints", []), days)


def fetch_ec2_metrics(session, region: str, instance_ids: list[str], days: int) -> dict[str, dict[str, Any]]:
    if not instance_ids:
        return {}
    cw = session.client("cloudwatch", region_name=region, config=BOTO_CONFIG)
    out: dict[str, dict[str, Any]] = {}
    for instance_id in instance_ids:
        cpu_series = _fetch_metric(
            cw,
            "AWS/EC2",
            "CPUUtilization",
            [{"Name": "InstanceId", "Value": instance_id}],
            days,
        )
        if not cpu_series:
            out[instance_id] = {"cpu": None, "memory": None, "series": {}}
            continue
        non_zero = [v for v in cpu_series if v > 0]
        cpu_avg = round(sum(cpu_series) / len(cpu_series), 2) if cpu_series else 0.0
        coverage = round(len(non_zero) / len(cpu_series), 2) if cpu_series else 0.0
        out[instance_id] = {
            "cpu": cpu_avg,
            "memory": None,
            "series": {"cpu": cpu_series},
            "coverage": coverage,
        }
    return out


def fetch_rds_metrics(session, region: str, db_identifiers: list[str], days: int) -> dict[str, dict[str, Any]]:
    if not db_identifiers:
        return {}
    cw = session.client("cloudwatch", region_name=region, config=BOTO_CONFIG)
    out: dict[str, dict[str, Any]] = {}
    for db_id in db_identifiers:
        cpu_series = _fetch_metric(
            cw,
            "AWS/RDS",
            "CPUUtilization",
            [{"Name": "DBInstanceIdentifier", "Value": db_id}],
            days,
        )
        if not cpu_series:
            out[db_id] = {"cpu": None, "memory": None, "series": {}}
            continue
        cpu_avg = round(sum(cpu_series) / len(cpu_series), 2)
        non_zero = [v for v in cpu_series if v > 0]
        coverage = round(len(non_zero) / len(cpu_series), 2)
        out[db_id] = {
            "cpu": cpu_avg,
            "memory": None,
            "series": {"cpu": cpu_series},
            "coverage": coverage,
        }
    return out


def fetch_metrics_for_resources(
    session,
    resources: list[dict[str, Any]],
    regions: list[str],
    days: int,
) -> dict[str, dict[str, Any]]:
    by_region_ec2: dict[str, list[str]] = {}
    by_region_rds: dict[str, list[str]] = {}

    for r in resources:
        service = r.get("service")
        region = r.get("region")
        cloud_id = r.get("cloud_id")
        if not region or not cloud_id:
            continue
        if service == "EC2":
            by_region_ec2.setdefault(region, []).append(cloud_id)
        elif service == "RDS":
            identifier = cloud_id.split(":")[-1] if ":" in cloud_id else cloud_id
            by_region_rds.setdefault(region, []).append(identifier)

    out: dict[str, dict[str, Any]] = {}

    for region, ids in by_region_ec2.items():
        metrics = fetch_ec2_metrics(session, region, ids, days)
        for cid, data in metrics.items():
            out[cid] = data

    for region, ids in by_region_rds.items():
        metrics = fetch_rds_metrics(session, region, ids, days)
        for identifier, data in metrics.items():
            for r in resources:
                if r.get("service") == "RDS" and r.get("cloud_id", "").endswith(identifier):
                    out[r["cloud_id"]] = data
                    break

    return out