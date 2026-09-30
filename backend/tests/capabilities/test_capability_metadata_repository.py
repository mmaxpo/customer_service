from uuid import uuid4

import pytest

from app.tcos.capabilities.repository import CapabilityMetadataRepository
from app.models.models import CapabilityMetadata


@pytest.mark.asyncio
async def test_capability_metadata_repository_get_list_delete_with_fake_session():
    tenant_id = uuid4()
    row = CapabilityMetadata(
        id=uuid4(),
        capability_id="runtime.response",
        tenant_id=tenant_id,
        display_name="Tenant Response",
        domain="customer_service",
        category="communication",
        tags=["reply"],
        extra={"priority": "high"},
        is_enabled=True,
    )

    class FakeScalarResult:
        def __init__(self, rows):
            self.rows = rows

        def all(self):
            return self.rows

    class FakeResult:
        def __init__(self, rows):
            self.rows = rows

        def scalar_one_or_none(self):
            return self.rows[0] if self.rows else None

        def scalars(self):
            return FakeScalarResult(self.rows)

    class FakeSession:
        def __init__(self):
            self.rows = [row]
            self.deleted = []

        async def execute(self, *_args, **_kwargs):
            return FakeResult(self.rows)

        async def delete(self, row):
            self.deleted.append(row)
            self.rows.remove(row)

        async def commit(self):
            pass

    session = FakeSession()
    repo = CapabilityMetadataRepository(session)

    loaded = await repo.get(capability_id="runtime.response", tenant_id=tenant_id)
    assert loaded is row

    rows = await repo.list_for_tenant(tenant_id=tenant_id)
    assert rows == [row]

    deleted = await repo.delete(capability_id="runtime.response", tenant_id=tenant_id)
    assert deleted is True
    assert session.deleted == [row]
    assert await repo.get(capability_id="runtime.response", tenant_id=tenant_id) is None
