import pytest
from types import SimpleNamespace

from app.runtime.nodes.executor import call_node


class FakeMcpSearch:
    async def search(self, q: str, k: int):
        class R:
            content = "OK"
            artifact = {"ok": True, "query": q, "results": [{"title": "t"}]}

        return R()


class FakeTools:
    mcp_search = FakeMcpSearch()


@pytest.mark.asyncio
async def test_web_search_golden_shape():
    ctx = SimpleNamespace(
        request=SimpleNamespace(state=SimpleNamespace(tools=FakeTools())),
        db=None,
        user_id=None,
    )

    node_def = {
        "id": "n1",
        "data": {"nodeType": "web.search", "query": "hello", "k": 3, "save_as": "ws"},
    }
    state = {"vars": {}}

    res = await call_node(ctx, node_def, state)

    assert res["output"] == "RESULT"
    assert isinstance(res["patch"]["vars"]["ws"]["results"], list)
    r0 = res["patch"]["vars"]["ws"]["results"][0]
    assert set(r0.keys()) >= {"title", "link", "snippet"}
