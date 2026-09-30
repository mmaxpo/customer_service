from app.workflow_operations.diff.service import (
    WorkflowStateDiffService,
)


def test_workflow_state_diff_detects_changes():

    before = {
        "vars": {
            "a": 1,
        },
        "results": {
            "node1": "hello",
        },
        "errors": {},
        "last": "before",
        "meta": {
            "finished": ["a"],
            "skipped": [],
            "interrupt": None,
        },
    }

    after = {
        "vars": {
            "a": 2,
            "b": 3,
        },
        "results": {
            "node1": "world",
        },
        "errors": {
            "node2": "boom",
        },
        "last": "after",
        "meta": {
            "finished": ["a", "b"],
            "skipped": ["x"],
            "interrupt": {
                "type": "approval",
            },
        },
    }

    diff = WorkflowStateDiffService().compare_states(
        before=before,
        after=after,
    )

    assert diff["changed"] is True

    assert diff["vars_changed"]["changed"] is True
    assert "b" in diff["vars_changed"]["added"]

    assert diff["results_changed"]["changed"] is True
    assert diff["errors_changed"]["changed"] is True

    assert diff["finished_changed"]["changed"] is True
    assert diff["skipped_changed"]["changed"] is True

    assert diff["last_changed"] is True
    assert diff["interrupt_changed"] is True
