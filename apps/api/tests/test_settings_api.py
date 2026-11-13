def test_get_settings_defaults(client, seeded_tenant):
    r = client.get("/api/v1/settings")
    assert r.status_code == 200
    body = r.json()
    assert "policies" in body
    assert "thresholds" in body
    assert body["llm"]["provider"] == "openai"


def test_update_policies(client, seeded_tenant):
    policies = [
        {
            "id": "test.rule",
            "scope": "Test",
            "description": "A test rule",
            "enabled": True,
            "requiresApproval": True,
            "blockAutoExecution": False,
        }
    ]
    r = client.put("/api/v1/settings/policies", json={"policies": policies})
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.get("/api/v1/settings")
    assert r.json()["policies"][0]["id"] == "test.rule"


def test_update_thresholds(client, seeded_tenant):
    thresholds = [
        {
            "id": "cpu",
            "label": "CPU",
            "description": "CPU threshold",
            "value": 20,
            "unit": "%",
            "minimum": 5,
            "maximum": 40,
        }
    ]
    r = client.put("/api/v1/settings/thresholds", json={"thresholds": thresholds})
    assert r.status_code == 200

    r = client.get("/api/v1/settings")
    assert r.json()["thresholds"][0]["value"] == 20


def test_update_llm(client, seeded_tenant):
    payload = {
        "llm": {
            "provider": "azure-openai",
            "model": "gpt-4o",
            "temperature": 0.1,
            "maxTokens": 4096,
            "cacheEnabled": False,
            "compactToolOutputs": True,
            "promptVersion": "2026-10-01",
        }
    }
    r = client.put("/api/v1/settings/llm", json=payload)
    assert r.status_code == 200
    assert r.json()["provider"] == "azure-openai"

    r = client.get("/api/v1/settings")
    assert r.json()["llm"]["model"] == "gpt-4o"