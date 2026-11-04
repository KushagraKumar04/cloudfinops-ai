from datetime import date
from unittest.mock import MagicMock

from app.services.aws_costs import fetch_costs


def test_fetch_costs_parses_daily_groups():
    ce = MagicMock()
    ce.get_cost_and_usage.return_value = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2026-10-01", "End": "2026-10-02"},
                "Groups": [
                    {
                        "Keys": ["Amazon Elastic Compute Cloud - Compute", "us-east-1"],
                        "Metrics": {"UnblendedCost": {"Amount": "42.50", "Unit": "USD"}},
                    },
                    {
                        "Keys": ["Amazon Simple Storage Service", "us-east-1"],
                        "Metrics": {"UnblendedCost": {"Amount": "5.00", "Unit": "USD"}},
                    },
                ],
            }
        ]
    }
    session = MagicMock()
    session.client.return_value = ce

    result = fetch_costs(session, date(2026, 10, 1), date(2026, 10, 1))
    assert len(result) == 2
    services = {r["service"] for r in result}
    assert "Amazon Elastic Compute Cloud - Compute" in services
    assert all(r["date"] == "2026-10-01" for r in result)


def test_fetch_costs_skips_zero_amounts():
    ce = MagicMock()
    ce.get_cost_and_usage.return_value = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2026-10-01", "End": "2026-10-02"},
                "Groups": [
                    {
                        "Keys": ["Zero Service", "us-east-1"],
                        "Metrics": {"UnblendedCost": {"Amount": "0", "Unit": "USD"}},
                    }
                ],
            }
        ]
    }
    session = MagicMock()
    session.client.return_value = ce

    result = fetch_costs(session, date(2026, 10, 1), date(2026, 10, 1))
    assert result == []