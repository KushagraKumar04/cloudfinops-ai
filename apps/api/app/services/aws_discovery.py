import logging
from typing import Any

from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger("app.aws.discovery")

BOTO_CONFIG = Config(
    retries={"max_attempts": 5, "mode": "adaptive"},
    connect_timeout=10,
    read_timeout=30,
    max_pool_connections=20,
)


def _tag_dict(tags: list[dict[str, str]] | None) -> dict[str, str]:
    if not tags:
        return {}
    return {t.get("Key", ""): t.get("Value", "") for t in tags}


def _env_from_tags(tags: dict[str, str]) -> str:
    for key in ("env", "Environment", "environment", "ENV"):
        if key in tags:
            return tags[key].lower()
    return "unknown"


def _app_from_tags(tags: dict[str, str]) -> str:
    for key in ("app", "Application", "application", "service", "Service"):
        if key in tags:
            return tags[key]
    return "unknown"


def _owner_from_tags(tags: dict[str, str]) -> str:
    for key in ("owner", "Owner", "team", "Team"):
        if key in tags:
            return tags[key]
    return "unassigned"


def _resource(
    cloud_id: str,
    name: str,
    rtype: str,
    service: str,
    region: str,
    status: str,
    tags: dict[str, str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = {
        "cloud_id": cloud_id,
        "name": name,
        "type": rtype,
        "service": service,
        "region": region,
        "environment": _env_from_tags(tags),
        "status": status,
        "application": _app_from_tags(tags),
        "owner": _owner_from_tags(tags),
        "tags": [{"key": k, "value": v} for k, v in tags.items()],
        "utilization": {},
        "series": {},
        "metric_coverage": 0.0,
        "monthly_cost": 0.0,
    }
    if extra:
        base.update(extra)
    return base


def discover_ec2(session, regions: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for region in regions:
        try:
            ec2 = session.client("ec2", region_name=region, config=BOTO_CONFIG)
            paginator = ec2.get_paginator("describe_instances")
            for page in paginator.paginate():
                for reservation in page.get("Reservations", []):
                    for inst in reservation.get("Instances", []):
                        state = inst.get("State", {}).get("Name", "unknown")
                        if state in ("terminated", "shutting-down"):
                            continue
                        tags = _tag_dict(inst.get("Tags"))
                        out.append(
                            _resource(
                                cloud_id=inst["InstanceId"],
                                name=tags.get("Name", inst["InstanceId"]),
                                rtype=f"EC2 {inst.get('InstanceType', 'unknown')}",
                                service="EC2",
                                region=region,
                                status=state,
                                tags=tags,
                            )
                        )
        except (ClientError, BotoCoreError) as exc:
            logger.warning("EC2 discovery failed in %s: %s", region, exc)
    return out


def discover_rds(session, regions: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for region in regions:
        try:
            rds = session.client("rds", region_name=region, config=BOTO_CONFIG)
            paginator = rds.get_paginator("describe_db_instances")
            for page in paginator.paginate():
                for db in page.get("DBInstances", []):
                    tags = _tag_dict(db.get("TagList"))
                    out.append(
                        _resource(
                            cloud_id=db["DBInstanceArn"],
                            name=db.get("DBInstanceIdentifier", ""),
                            rtype=f"RDS {db.get('DBInstanceClass', 'unknown')}",
                            service="RDS",
                            region=region,
                            status=db.get("DBInstanceStatus", "unknown"),
                            tags=tags,
                        )
                    )
        except (ClientError, BotoCoreError) as exc:
            logger.warning("RDS discovery failed in %s: %s", region, exc)
    return out


def discover_ebs(session, regions: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for region in regions:
        try:
            ec2 = session.client("ec2", region_name=region, config=BOTO_CONFIG)
            paginator = ec2.get_paginator("describe_volumes")
            for page in paginator.paginate():
                for vol in page.get("Volumes", []):
                    attachments = vol.get("Attachments", [])
                    state = "in-use" if attachments else "unattached"
                    tags = _tag_dict(vol.get("Tags"))
                    size = vol.get("Size", 0)
                    vtype = vol.get("VolumeType", "gp2")
                    out.append(
                        _resource(
                            cloud_id=vol["VolumeId"],
                            name=tags.get("Name", vol["VolumeId"]),
                            rtype=f"EBS {vtype} {size}GB",
                            service="EBS",
                            region=region,
                            status=state,
                            tags=tags,
                        )
                    )
        except (ClientError, BotoCoreError) as exc:
            logger.warning("EBS discovery failed in %s: %s", region, exc)
    return out


def discover_eip(session, regions: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for region in regions:
        try:
            ec2 = session.client("ec2", region_name=region, config=BOTO_CONFIG)
            response = ec2.describe_addresses()
            for addr in response.get("Addresses", []):
                tags = _tag_dict(addr.get("Tags"))
                associated = "association_id" in addr or "InstanceId" in addr
                out.append(
                    _resource(
                        cloud_id=addr.get("AllocationId", addr.get("PublicIp", "")),
                        name=tags.get("Name", addr.get("PublicIp", "")),
                        rtype="Elastic IP",
                        service="Networking",
                        region=region,
                        status="available" if associated else "unattached",
                        tags=tags,
                    )
                )
        except (ClientError, BotoCoreError) as exc:
            logger.warning("EIP discovery failed in %s: %s", region, exc)
    return out


def discover_eks(session, regions: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for region in regions:
        try:
            eks = session.client("eks", region_name=region, config=BOTO_CONFIG)
            response = eks.list_clusters()
            for cluster_name in response.get("clusters", []):
                try:
                    detail = eks.describe_cluster(name=cluster_name).get("cluster", {})
                except (ClientError, BotoCoreError):
                    continue
                tags = detail.get("tags") or {}
                out.append(
                    _resource(
                        cloud_id=detail.get("arn", cluster_name),
                        name=cluster_name,
                        rtype="EKS cluster",
                        service="EKS",
                        region=region,
                        status=detail.get("status", "active").lower(),
                        tags=tags,
                    )
                )
        except (ClientError, BotoCoreError) as exc:
            logger.warning("EKS discovery failed in %s: %s", region, exc)
    return out


def discover_s3(session, account_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        s3 = session.client("s3", config=BOTO_CONFIG)
        response = s3.list_buckets()
        for bucket in response.get("Buckets", []):
            name = bucket.get("Name", "")
            try:
                location = s3.get_bucket_location(Bucket=name).get("LocationConstraint") or "us-east-1"
            except (ClientError, BotoCoreError):
                location = "unknown"
            try:
                tagging = s3.get_bucket_tagging(Bucket=name)
                tags = _tag_dict(tagging.get("TagSet"))
            except (ClientError, BotoCoreError):
                tags = {}
            out.append(
                _resource(
                    cloud_id=f"arn:aws:s3:::{name}",
                    name=name,
                    rtype="S3 bucket",
                    service="S3",
                    region=location,
                    status="active",
                    tags=tags,
                )
            )
    except (ClientError, BotoCoreError) as exc:
        logger.warning("S3 discovery failed for %s: %s", account_id, exc)
    return out


SERVICE_DISPATCH = {
    "EC2": lambda session, regions: discover_ec2(session, regions),
    "RDS": lambda session, regions: discover_rds(session, regions),
    "EBS": lambda session, regions: discover_ebs(session, regions),
    "EIP": lambda session, regions: discover_eip(session, regions),
    "EKS": lambda session, regions: discover_eks(session, regions),
}


def discover_all(
    session,
    account_id: str,
    regions: list[str],
    enabled_services: list[str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name in enabled_services:
        name = name.strip().upper()
        if name == "S3":
            out.extend(discover_s3(session, account_id))
            continue
        fn = SERVICE_DISPATCH.get(name)
        if fn is None:
            continue
        try:
            out.extend(fn(session, regions))
        except (ClientError, BotoCoreError) as exc:
            logger.warning("%s discovery failed: %s", name, exc)
    return out