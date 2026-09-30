from __future__ import annotations

from app.runtime.engine.validator import validate_workflow


def _code(e) -> str:
    # Support both dict errors and ValidationError objects
    if isinstance(e, dict):
        return e.get("code", "")
    return getattr(e, "code", "")


def _codes(errs) -> set[str]:
    return {_code(e) for e in (errs or [])}


def test_validator_invalid_edge_missing_node():
    wf = {
        "nodes": [
            {"id": "t1", "data": {"nodeType": "trigger.message", "input": "hi"}},
            {"id": "r1", "data": {"nodeType": "response"}},
        ],
        "edges": [
            {"id": "e1", "source": "t1", "target": "MISSING_NODE"},
        ],
    }

    errors = validate_workflow(wf)
    codes = _codes(errors)

    assert "edge_invalid_endpoint" in codes
    assert "unreachable_response" in codes


def test_validator_unreachable_response():
    wf = {
        "nodes": [
            {"id": "t1", "data": {"nodeType": "trigger.message", "input": "hi"}},
            {
                "id": "x1",
                "data": {"nodeType": "set.variable", "key": "k", "value": "v"},
            },
            {"id": "r1", "data": {"nodeType": "response"}},
        ],
        "edges": [
            {"id": "e1", "source": "t1", "target": "x1"},
            # response has no path from trigger
        ],
    }

    errors = validate_workflow(wf)
    codes = _codes(errors)

    assert "unreachable_response" in codes


def test_validator_cycle_detected():
    # trigger -> a -> b -> a  (cycle)
    wf = {
        "nodes": [
            {"id": "t1", "data": {"nodeType": "trigger.message", "input": "hi"}},
            {"id": "a", "data": {"nodeType": "set.variable", "key": "a", "value": "A"}},
            {"id": "b", "data": {"nodeType": "set.variable", "key": "b", "value": "B"}},
            {"id": "r1", "data": {"nodeType": "response"}},
        ],
        "edges": [
            {"id": "e1", "source": "t1", "target": "a"},
            {"id": "e2", "source": "a", "target": "b"},
            {"id": "e3", "source": "b", "target": "a"},  # cycle
            {"id": "e4", "source": "b", "target": "r1"},
        ],
    }

    errors = validate_workflow(wf)
    codes = _codes(errors)

    assert "cycle_detected" in codes


def test_validator_rejects_invalid_when():
    wf = {
        "nodes": [
            {"id": "t1", "data": {"nodeType": "trigger.message", "input": "x"}},
            {
                "id": "rtr",
                "data": {
                    "nodeType": "router.rules",
                    "rules": [],
                    "default_route": "billing",
                },
            },
            {"id": "a", "data": {"nodeType": "set.variable", "key": "x", "value": "1"}},
            {"id": "resp", "data": {"nodeType": "response"}},
        ],
        "edges": [
            {"id": "e1", "source": "t1", "target": "rtr"},
            {
                "id": "e2",
                "source": "rtr",
                "target": "a",
                "when": {"or": [{"eq": ["vars.route_key", "billing"]}]},
            },  # invalid in v1
            {"id": "e3", "source": "a", "target": "resp"},
        ],
    }
    errs = validate_workflow(wf)
    codes = _codes(errs)
    assert "invalid_when" in codes
