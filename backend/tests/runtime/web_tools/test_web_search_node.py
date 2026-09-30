import pytest
from types import SimpleNamespace

from app.runtime.nodes.executor import call_node, apply_node_result


class FakeMcpSearch:
    async def search(self, q: str, k: int):
        class R:
            content = "OK"
            artifact = {"ok": True, "query": q, "results": [{"title": "t"}]}

        return R()


class FakeTools:
    mcp_search = FakeMcpSearch()


@pytest.mark.asyncio
async def test_web_search_reads_query_and_sets_vars():
    ctx = SimpleNamespace(
        request=SimpleNamespace(state=SimpleNamespace(tools=FakeTools())),
        db=None,
        user_id=None,
    )

    node_def = {
        "id": "n1",
        "data": {
            "nodeType": "web.search",
            "query": "hello",
            "k": 3,
            "artifact_as": "ws",  # ✅ changed
        },
    }
    state = {"vars": {}}

    res = await call_node(ctx, node_def, state)
    assert res["output"] == "RESULT"
    assert res["patch"]["vars"]["ws"]["results"][0]["title"] == "t"

    merged = apply_node_result(state, node_def, res)
    assert merged["vars"]["ws"]["results"][0]["title"] == "t"
