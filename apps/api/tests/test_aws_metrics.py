from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from app.services.aws_metrics import fetch_ec2_metrics, fetch_metrics_for_resources


def test_fetch_ec2_metrics_returns_series():
    today = datetime.now(UTC)
    datapoints = [
        {"Timestamp": today - timedelta(days=i), "Average": 10.0 + i} for i in range(5)
    ]
    cw = MagicMock()
    cw.get_metric_statistics.return_value = {"Datapoints": datapoints}
    session = MagicMock()
    session.client.return_value = cw

    result = fetch_ec2_metrics(session, "us-east-1", ["i-abc"], 7)
    assert "i-abc" in result
    assert result["i-abc"]["cpu"] is not None
    assert len(result["i-abc"]["series"]["cpu"]) == 7


def test_fetch_metrics_for_resources_splits_by_region():
    today = datetime.now(UTC)
    cw = MagicMock()
    cw.get_metric_statistics.return_value = {
        "Datapoints": [{"Timestamp": today, "Average": 20.0}]
    }
    session = MagicMock()
    session.client.return_value = cw

    resources = [
        {"cloud_id": "i-a", "service": "EC2", "region": "us-east-1"},
        {"cloud_id": "i-b", "service": "EC2", "region": "us-west-2"},
    ]
    result = fetch_metrics_for_resources(session, resources, ["us-east-1", "us-west-2"], 3)
    assert "i-a" in result
    assert "i-b" in result