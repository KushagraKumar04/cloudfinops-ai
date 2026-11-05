from unittest.mock import MagicMock

from app.services.aws_discovery import (
    discover_ebs,
    discover_ec2,
    discover_eip,
    discover_eks,
    discover_rds,
    discover_s3,
)


def _paginator(pages):
    class FakePaginator:
        def paginate(self, **kwargs):
            for p in pages:
                yield p

    return FakePaginator()


def test_discover_ec2_returns_resources():
    ec2 = MagicMock()
    ec2.get_paginator.return_value = _paginator(
        [
            {
                "Reservations": [
                    {
                        "Instances": [
                            {
                                "InstanceId": "i-abc",
                                "InstanceType": "m5.large",
                                "State": {"Name": "running"},
                                "Tags": [
                                    {"Key": "Name", "Value": "api-1"},
                                    {"Key": "env", "Value": "prod"},
                                ],
                            }
                        ]
                    }
                ]
            }
        ]
    )
    session = MagicMock()
    session.client.return_value = ec2

    result = discover_ec2(session, ["us-east-1"])
    assert len(result) == 1
    assert result[0]["cloud_id"] == "i-abc"
    assert result[0]["service"] == "EC2"
    assert result[0]["environment"] == "prod"
    assert result[0]["status"] == "running"


def test_discover_ec2_skips_terminated():
    ec2 = MagicMock()
    ec2.get_paginator.return_value = _paginator(
        [
            {
                "Reservations": [
                    {"Instances": [{"InstanceId": "i-x", "State": {"Name": "terminated"}}]}
                ]
            }
        ]
    )
    session = MagicMock()
    session.client.return_value = ec2

    result = discover_ec2(session, ["us-east-1"])
    assert result == []


def test_discover_rds():
    rds = MagicMock()
    rds.get_paginator.return_value = _paginator(
        [
            {
                "DBInstances": [
                    {
                        "DBInstanceArn": "arn:aws:rds:us-east-1:123:db:prod",
                        "DBInstanceIdentifier": "prod-db",
                        "DBInstanceClass": "db.r5.large",
                        "DBInstanceStatus": "available",
                        "TagList": [],
                    }
                ]
            }
        ]
    )
    session = MagicMock()
    session.client.return_value = rds

    result = discover_rds(session, ["us-east-1"])
    assert len(result) == 1
    assert result[0]["service"] == "RDS"


def test_discover_ebs_marks_unattached():
    ec2 = MagicMock()
    ec2.get_paginator.return_value = _paginator(
        [
            {
                "Volumes": [
                    {
                        "VolumeId": "vol-1",
                        "Size": 500,
                        "VolumeType": "gp3",
                        "Attachments": [],
                        "Tags": [],
                    },
                    {
                        "VolumeId": "vol-2",
                        "Size": 100,
                        "VolumeType": "gp2",
                        "Attachments": [{"InstanceId": "i-abc"}],
                        "Tags": [],
                    },
                ]
            }
        ]
    )
    session = MagicMock()
    session.client.return_value = ec2

    result = discover_ebs(session, ["us-east-1"])
    assert len(result) == 2
    statuses = {r["cloud_id"]: r["status"] for r in result}
    assert statuses["vol-1"] == "unattached"
    assert statuses["vol-2"] == "in-use"


def test_discover_s3():
    s3 = MagicMock()
    s3.list_buckets.return_value = {"Buckets": [{"Name": "acme-logs"}]}
    s3.get_bucket_location.return_value = {"LocationConstraint": "us-west-2"}
    s3.get_bucket_tagging.return_value = {"TagSet": [{"Key": "env", "Value": "prod"}]}
    session = MagicMock()
    session.client.return_value = s3

    result = discover_s3(session, "123456789012")
    assert len(result) == 1
    assert result[0]["cloud_id"] == "arn:aws:s3:::acme-logs"
    assert result[0]["region"] == "us-west-2"


def test_discover_eip():
    ec2 = MagicMock()
    ec2.describe_addresses.return_value = {
        "Addresses": [
            {"AllocationId": "eipalloc-1", "PublicIp": "1.2.3.4", "Tags": []},
            {
                "AllocationId": "eipalloc-2",
                "PublicIp": "5.6.7.8",
                "InstanceId": "i-abc",
                "Tags": [{"Key": "Name", "Value": "used"}],
            },
        ]
    }
    session = MagicMock()
    session.client.return_value = ec2

    result = discover_eip(session, ["us-east-1"])
    assert len(result) == 2
    statuses = {r["cloud_id"]: r["status"] for r in result}
    assert statuses["eipalloc-1"] == "unattached"
    assert statuses["eipalloc-2"] == "available"


def test_discover_eks():
    eks = MagicMock()
    eks.list_clusters.return_value = {"clusters": ["prod-eks"]}
    eks.describe_cluster.return_value = {
        "cluster": {
            "arn": "arn:aws:eks:us-east-1:123:cluster/prod-eks",
            "status": "ACTIVE",
            "tags": {"env": "prod"},
        }
    }
    session = MagicMock()
    session.client.return_value = eks

    result = discover_eks(session, ["us-east-1"])
    assert len(result) == 1
    assert result[0]["name"] == "prod-eks"