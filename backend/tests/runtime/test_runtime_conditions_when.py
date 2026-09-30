from app.runtime.engine.router import eval_when


def test_eval_when_eq_route_key_matches():
    state = {"vars": {"route_key": "billing"}}
    assert eval_when({"eq": ["vars.route_key", "billing"]}, state) is True
    assert eval_when({"eq": ["vars.route_key", "refund"]}, state) is False


def test_eval_when_none_is_true():
    assert eval_when(None, {"vars": {}}) is True


def test_eval_when_invalid_returns_false():
    assert eval_when({}, {"vars": {"route_key": "billing"}}) is False
    assert (
        eval_when({"eq": ["vars.route_key"]}, {"vars": {"route_key": "billing"}})
        is False
    )
