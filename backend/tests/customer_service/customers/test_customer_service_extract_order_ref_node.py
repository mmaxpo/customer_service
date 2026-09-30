import pytest

from app.domains.customer_service.runtime.nodes.order_ref import ExtractOrderRefConfig, ExtractOrderRefNode


@pytest.mark.asyncio
async def test_extract_order_ref_from_hash_number():
    result = await ExtractOrderRefNode().run(
        ctx=None,
        state={"last": "Where is my order #1005?"},
        config=ExtractOrderRefConfig(),
    )

    assert result["output"] == "#1005"
    assert result["patch"]["vars"]["order_ref"] == "#1005"
    assert result["patch"]["vars"]["order_ref_found"] is True


@pytest.mark.asyncio
async def test_extract_order_ref_from_order_number_phrase():
    result = await ExtractOrderRefNode().run(
        ctx=None,
        state={"last": "Can you check order number 1003 please?"},
        config=ExtractOrderRefConfig(),
    )

    assert result["output"] == "#1003"


@pytest.mark.asyncio
async def test_extract_order_ref_returns_empty_when_missing():
    result = await ExtractOrderRefNode().run(
        ctx=None,
        state={"last": "Where is my package?"},
        config=ExtractOrderRefConfig(),
    )

    assert result["output"] == ""
    assert result["patch"]["vars"]["order_ref_found"] is False
