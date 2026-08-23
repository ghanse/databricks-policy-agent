from datetime import UTC, datetime

from policy_agent.storage.delta import _to_statement_parameters


def _by_name(items):
    return {item.name: item for item in items}


def test_statement_parameter_type_inference():
    params = _to_statement_parameters(
        {
            "text": "hello",
            "count": 3,
            "ratio": 1.5,
            "flag": True,
            "when": datetime(2026, 1, 1, tzinfo=UTC),
            "empty": None,
        }
    )
    by_name = _by_name(params)
    assert (by_name["text"].value, by_name["text"].type) == ("hello", "STRING")
    assert (by_name["count"].value, by_name["count"].type) == ("3", "BIGINT")
    assert (by_name["ratio"].value, by_name["ratio"].type) == ("1.5", "DOUBLE")
    assert (by_name["flag"].value, by_name["flag"].type) == ("true", "BOOLEAN")
    assert by_name["when"].type == "TIMESTAMP"
    assert by_name["empty"].value is None


def test_no_parameters_returns_none():
    assert _to_statement_parameters(None) is None
    assert _to_statement_parameters({}) is None
