import pytest
from types import SimpleNamespace

from app.runtime.nodes.executor import call_node
from app.tools.common.types import ToolResult


class FakeWebFetchExtract:
    def __init__(self, html: str):
        self.html = html

    async def fetch_extract(self, url: str):
        # simulate extractor output
        return ToolResult(
            content="EXTRACTED",
            artifact={"url": url, "title": "T", "text": "EXTRACTED"},
        )


class FakeTools:
    def __init__(self):
        self.web_fetch_extract = FakeWebFetchExtract("<html>hi</html>")


@pytest.mark.asyncio
async def test_web_fetch_extract_sets_vars():
    ctx = SimpleNamespace(
        request=SimpleNamespace(state=SimpleNamespace(tools=FakeTools())),
        db=None,
        user_id=None,
    )

    node_def = {
        "id": "n2",
        "data": {
            "nodeType": "web.fetch_extract",
            "url": "https://example.com",
            "save_as": "page",
        },
    }
    state = {"vars": {}}

    res = await call_node(ctx, node_def, state)

    assert res["output"] == "EXTRACTED"
    assert res["patch"]["vars"]["page"]["url"] == "https://example.com"
    assert res["patch"]["vars"]["page"]["text"] == "EXTRACTED"
