from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.capabilities import router


def build_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_list_capabilities_endpoint():
    client = build_test_client()

    response = client.get("/capabilities")

    assert response.status_code == 200
    data = response.json()
    ids = {item["id"] for item in data["items"]}
    assert "runtime.agent_custom" in ids
    assert "runtime.response" in ids
    assert "agent_tool.knowledge_search" in ids


def test_search_capabilities_endpoint():
    client = build_test_client()

    response = client.get("/capabilities", params={"q": "shopify"})

    assert response.status_code == 200
    data = response.json()
    assert any("shopify" in item["id"] for item in data["items"])


def test_get_capability_endpoint():
    client = build_test_client()

    response = client.get("/capabilities/runtime.agent_custom")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "runtime.agent_custom"
    assert data["source"] == "runtime_node"
    assert data["source_ref"] == "agent.custom"


def test_list_capabilities_endpoint_filters_domain_and_limit():
    client = build_test_client()

    response = client.get("/capabilities", params={"domain": "knowledge", "limit": 2})

    assert response.status_code == 200
    items = response.json()["items"]
    assert 1 <= len(items) <= 2
    assert all(item["domain"] == "knowledge" for item in items)


def test_match_capability_candidates_endpoint():
    client = build_test_client()

    response = client.post(
        "/capabilities/match",
        json={"query": "knowledge", "limit": 5},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "knowledge"
    assert data["matches"]
    assert any(
        item["capability"]["id"] == "agent_tool.knowledge_search"
        for item in data["matches"]
    )


def test_list_tenant_capabilities_endpoint(monkeypatch):
    from app.tcos.capabilities.service import build_capability_registry

    async def fake_builder(*, db, tenant_id=None):
        return build_capability_registry()

    monkeypatch.setattr(
        "app.api.capabilities.build_capability_registry_for_tenant",
        fake_builder,
    )

    client = build_test_client()

    response = client.get("/capabilities/tenant", params={"q": "response"})

    assert response.status_code == 200
    data = response.json()
    assert any(item["id"] == "runtime.response" for item in data["items"])
