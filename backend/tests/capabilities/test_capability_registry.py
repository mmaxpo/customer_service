from app.tcos.capabilities.models import CapabilitySource
from app.tcos.capabilities.service import build_capability_registry


def test_capability_registry_wraps_runtime_nodes():
    registry = build_capability_registry()

    capability = registry.get("runtime.agent_custom")

    assert capability.source == CapabilitySource.RUNTIME_NODE
    assert capability.source_ref == "agent.custom"
    assert capability.input_schema
    assert capability.metadata["default_config"]["nodeType"] == "agent.custom"


def test_capability_registry_wraps_agent_tools():
    registry = build_capability_registry()

    capability = registry.get("agent_tool.knowledge_search")

    assert capability.source == CapabilitySource.AGENT_TOOL
    assert capability.source_ref == "knowledge_search"
    assert capability.input_schema["type"] == "object"


def test_capability_registry_searches_existing_capabilities():
    registry = build_capability_registry()

    results = registry.search("shopify")

    assert any(item.id == "agent_tool.fake_refund_order" for item in results) is False
    assert any("shopify" in item.id for item in results)


def test_capability_registry_lists_sorted_unique_capabilities():
    registry = build_capability_registry()
    items = registry.list()
    ids = [item.id for item in items]

    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))
    assert "runtime.response" in ids
    assert "agent_tool.calculator" in ids


def test_capability_registry_discover_filters_domain_and_limit():
    registry = build_capability_registry()

    items = registry.discover(domain="knowledge", limit=2)

    assert 1 <= len(items) <= 2
    assert all(item.domain == "knowledge" for item in items)


def test_sensitive_capability_has_lower_score_than_safe_capability():
    from app.tcos.capabilities.scoring import score_capability

    registry = build_capability_registry()

    safe = registry.get("runtime.response")
    sensitive = registry.get("runtime.human_approval")

    assert score_capability(safe) > score_capability(sensitive)


def test_capability_registry_compatible_filters_required_inputs():
    registry = build_capability_registry()

    items = registry.compatible(query="calculator", required_inputs=["expression"])

    assert any(item.id == "agent_tool.calculator" for item in items)


def test_capability_registry_compatible_rejects_missing_required_inputs():
    registry = build_capability_registry()

    items = registry.compatible(query="calculator", required_inputs=["order_id"])

    assert all(item.id != "agent_tool.calculator" for item in items)


def test_capability_registry_compatible_can_reject_approval_required():
    registry = build_capability_registry()

    items = registry.compatible(
        query="approval",
        allow_approval_required=False,
    )

    assert all(item.id != "runtime.human_approval" for item in items)


def test_apply_metadata_override_updates_capability_fields():
    from uuid import uuid4

    from app.tcos.capabilities.models import CapabilityStatus
    from app.tcos.capabilities.overrides import apply_metadata_override
    from app.models.models import CapabilityMetadata

    registry = build_capability_registry()
    capability = registry.get("runtime.response")

    override = CapabilityMetadata(
        id=uuid4(),
        capability_id=capability.id,
        tenant_id=None,
        display_name="Customer Response",
        description="Send the final customer-facing answer.",
        domain="customer_service",
        category="communication",
        status="stable",
        tags=["customer", "reply"],
        extra={"business_priority": "high"},
        is_enabled=True,
    )

    updated = apply_metadata_override(capability, override)

    assert updated is not None
    assert updated.title == "Customer Response"
    assert updated.description == "Send the final customer-facing answer."
    assert updated.domain == "customer_service"
    assert updated.category == "communication"
    assert updated.status == CapabilityStatus.STABLE
    assert updated.metadata["business_priority"] == "high"
    assert updated.metadata["tags"] == ["customer", "reply"]


def test_apply_metadata_override_can_disable_capability():
    from uuid import uuid4

    from app.tcos.capabilities.overrides import apply_metadata_override
    from app.models.models import CapabilityMetadata

    registry = build_capability_registry()
    capability = registry.get("runtime.response")

    override = CapabilityMetadata(
        id=uuid4(),
        capability_id=capability.id,
        tenant_id=None,
        tags=[],
        extra={},
        is_enabled=False,
    )

    assert apply_metadata_override(capability, override) is None


async def test_build_capability_registry_for_tenant_applies_overrides(monkeypatch):
    from uuid import uuid4

    from app.tcos.capabilities.service import build_capability_registry_for_tenant
    from app.models.models import CapabilityMetadata

    tenant_id = uuid4()

    class FakeRepo:
        def __init__(self, db):
            self.db = db

        async def list_for_tenant(self, *, tenant_id=None):
            return [
                CapabilityMetadata(
                    id=uuid4(),
                    capability_id="runtime.response",
                    tenant_id=tenant_id,
                    display_name="Tenant Response",
                    domain="customer_service",
                    category="communication",
                    tags=["tenant"],
                    extra={"source": "test"},
                    is_enabled=True,
                )
            ]

    monkeypatch.setattr(
        "app.tcos.capabilities.service.CapabilityMetadataRepository", FakeRepo
    )

    registry = await build_capability_registry_for_tenant(
        db=object(), tenant_id=tenant_id
    )
    capability = registry.get("runtime.response")

    assert capability.title == "Tenant Response"
    assert capability.domain == "customer_service"
    assert capability.category == "communication"
    assert capability.metadata["source"] == "test"
