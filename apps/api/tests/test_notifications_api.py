import uuid

from app.services.notifications import set_notifier_factory
from app.services.notifications.base import Notifier, SendResult


class _FakeNotifier:
    def __init__(self, channel: str, record: list) -> None:
        self.channel = channel
        self._record = record

    def send(self, destination: dict, subject: str, body: str) -> SendResult:
        self._record.append(
            {"channel": self.channel, "destination": destination, "subject": subject, "body": body}
        )
        return SendResult(ok=True, status="delivered", duration_ms=5)


def _install_fake_notifier():
    sent: list = []

    def factory(channel: str):
        return _FakeNotifier(channel, sent)

    set_notifier_factory(factory)
    return sent


def _teardown_fake_notifier():
    set_notifier_factory(None)


def test_list_rules_empty(client, seeded_tenant):
    r = client.get("/api/v1/notifications/rules")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert "cost.anomaly.detected" in body["eventTypes"]


def test_create_rule(client, seeded_tenant):
    r = client.post(
        "/api/v1/notifications/rules",
        json={
            "name": "Test rule",
            "eventType": "cost.anomaly.detected",
            "channel": "email",
            "destination": {"to": ["ops@example.com"]},
            "minSeverity": "warning",
            "enabled": True,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Test rule"
    assert body["enabled"] is True


def test_create_rule_duplicate_name(client, seeded_tenant):
    payload = {
        "name": "Dup",
        "eventType": "cost.anomaly.detected",
        "channel": "email",
        "destination": {"to": ["ops@example.com"]},
    }
    first = client.post("/api/v1/notifications/rules", json=payload)
    assert first.status_code == 201
    second = client.post("/api/v1/notifications/rules", json=payload)
    assert second.status_code == 409


def test_create_rule_unknown_event(client, seeded_tenant):
    r = client.post(
        "/api/v1/notifications/rules",
        json={
            "name": "Bad",
            "eventType": "not.a.real.event",
            "channel": "email",
            "destination": {"to": ["ops@example.com"]},
        },
    )
    assert r.status_code == 422


def test_update_rule(client, seeded_tenant):
    created = client.post(
        "/api/v1/notifications/rules",
        json={
            "name": "Update",
            "eventType": "cost.anomaly.detected",
            "channel": "email",
            "destination": {"to": ["ops@example.com"]},
        },
    ).json()
    r = client.put(
        f"/api/v1/notifications/rules/{created['id']}",
        json={"enabled": False, "minSeverity": "critical"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["minSeverity"] == "critical"


def test_delete_rule(client, seeded_tenant):
    created = client.post(
        "/api/v1/notifications/rules",
        json={
            "name": "Delete me",
            "eventType": "cost.anomaly.detected",
            "channel": "email",
            "destination": {"to": ["ops@example.com"]},
        },
    ).json()
    r = client.delete(f"/api/v1/notifications/rules/{created['id']}")
    assert r.status_code == 204

    missing = client.put(
        f"/api/v1/notifications/rules/{created['id']}",
        json={"enabled": False},
    )
    assert missing.status_code == 404


def test_dispatch_matching_rule(client, seeded_tenant):
    sent = _install_fake_notifier()
    try:
        client.post(
            "/api/v1/notifications/rules",
            json={
                "name": "Dispatch rule",
                "eventType": "cost.anomaly.detected",
                "channel": "email",
                "destination": {"to": ["ops@example.com"]},
                "minSeverity": "warning",
            },
        )
        r = client.post(
            "/api/v1/notifications/dispatch",
            json={
                "eventType": "cost.anomaly.detected",
                "severity": "warning",
                "subject": "Test anomaly",
                "body": "EC2 up 42%",
            },
        )
        assert r.status_code == 200
        assert r.json()["total"] == 1
        assert len(sent) == 1
        assert sent[0]["channel"] == "email"
        assert sent[0]["subject"] == "Test anomaly"
    finally:
        _teardown_fake_notifier()


def test_dispatch_below_min_severity_skipped(client, seeded_tenant):
    sent = _install_fake_notifier()
    try:
        client.post(
            "/api/v1/notifications/rules",
            json={
                "name": "Critical only",
                "eventType": "cost.anomaly.detected",
                "channel": "email",
                "destination": {"to": ["ops@example.com"]},
                "minSeverity": "critical",
            },
        )
        r = client.post(
            "/api/v1/notifications/dispatch",
            json={
                "eventType": "cost.anomaly.detected",
                "severity": "info",
                "subject": "Info event",
                "body": "should not fire",
            },
        )
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert len(sent) == 0
    finally:
        _teardown_fake_notifier()


def test_dispatch_disabled_rule_skipped(client, seeded_tenant):
    sent = _install_fake_notifier()
    try:
        created = client.post(
            "/api/v1/notifications/rules",
            json={
                "name": "Disabled rule",
                "eventType": "cost.anomaly.detected",
                "channel": "email",
                "destination": {"to": ["ops@example.com"]},
                "enabled": False,
            },
        ).json()
        assert created["enabled"] is False

        r = client.post(
            "/api/v1/notifications/dispatch",
            json={
                "eventType": "cost.anomaly.detected",
                "severity": "critical",
                "subject": "Should skip",
                "body": "",
            },
        )
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert len(sent) == 0
    finally:
        _teardown_fake_notifier()


def test_test_endpoint(client, seeded_tenant):
    sent = _install_fake_notifier()
    try:
        created = client.post(
            "/api/v1/notifications/rules",
            json={
                "name": "Test rule",
                "eventType": "cost.anomaly.detected",
                "channel": "email",
                "destination": {"to": ["ops@example.com"]},
            },
        ).json()
        r = client.post(f"/api/v1/notifications/rules/{created['id']}/test")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "delivered"
        assert body["eventType"] == "test"
        assert len(sent) == 1
    finally:
        _teardown_fake_notifier()


def test_list_deliveries(client, seeded_tenant):
    sent = _install_fake_notifier()
    try:
        client.post(
            "/api/v1/notifications/rules",
            json={
                "name": "L",
                "eventType": "cost.anomaly.detected",
                "channel": "email",
                "destination": {"to": ["ops@example.com"]},
            },
        )
        client.post(
            "/api/v1/notifications/dispatch",
            json={
                "eventType": "cost.anomaly.detected",
                "severity": "critical",
                "subject": "A",
                "body": "",
            },
        )
        r = client.get("/api/v1/notifications")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["totals"].get("delivered", 0) == 1
    finally:
        _teardown_fake_notifier()


def test_unknown_rule_404(client, seeded_tenant):
    r = client.post(f"/api/v1/notifications/rules/{uuid.uuid4()}/test")
    assert r.status_code == 404

def test_list_returns_unread_count(client, seeded_tenant):
    sent = _install_fake_notifier()
    try:
        client.post(
            "/api/v1/notifications/rules",
            json={
                "name": "Unread rule",
                "eventType": "cost.anomaly.detected",
                "channel": "email",
                "destination": {"to": ["ops@example.com"]},
            },
        )
        client.post(
            "/api/v1/notifications/dispatch",
            json={
                "eventType": "cost.anomaly.detected",
                "severity": "critical",
                "subject": "Unread A",
                "body": "",
            },
        )
        r = client.get("/api/v1/notifications")
        assert r.status_code == 200
        body = r.json()
        assert body["unread"] == 1
    finally:
        _teardown_fake_notifier()


def test_mark_single_read(client, seeded_tenant):
    sent = _install_fake_notifier()
    try:
        client.post(
            "/api/v1/notifications/rules",
            json={
                "name": "Mark rule",
                "eventType": "cost.anomaly.detected",
                "channel": "email",
                "destination": {"to": ["ops@example.com"]},
            },
        )
        created = client.post(
            "/api/v1/notifications/dispatch",
            json={
                "eventType": "cost.anomaly.detected",
                "severity": "critical",
                "subject": "A",
                "body": "",
            },
        ).json()
        notification_id = created["items"][0]["id"]

        r = client.post(f"/api/v1/notifications/{notification_id}/read")
        assert r.status_code == 200
        assert r.json()["readAt"] is not None

        after = client.get("/api/v1/notifications").json()
        assert after["unread"] == 0
    finally:
        _teardown_fake_notifier()


def test_mark_all_read(client, seeded_tenant):
    sent = _install_fake_notifier()
    try:
        client.post(
            "/api/v1/notifications/rules",
            json={
                "name": "All read",
                "eventType": "cost.anomaly.detected",
                "channel": "email",
                "destination": {"to": ["ops@example.com"]},
            },
        )
        for i in range(3):
            client.post(
                "/api/v1/notifications/dispatch",
                json={
                    "eventType": "cost.anomaly.detected",
                    "severity": "critical",
                    "subject": f"N{i}",
                    "body": "",
                },
            )
        before = client.get("/api/v1/notifications").json()
        assert before["unread"] == 3

        r = client.post("/api/v1/notifications/read-all")
        assert r.status_code == 200
        assert r.json()["markedRead"] == 3

        after = client.get("/api/v1/notifications").json()
        assert after["unread"] == 0
    finally:
        _teardown_fake_notifier()


def test_mark_unknown_notification_404(client, seeded_tenant):
    r = client.post(f"/api/v1/notifications/{uuid.uuid4()}/read")
    assert r.status_code == 404