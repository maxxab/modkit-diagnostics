import importlib

import pytest


def redact(value, **kwargs):
    module = importlib.import_module("modkit_diagnostics")
    assert hasattr(module, "redact"), "bounded redaction API missing"
    return module.redact(value, **kwargs)


def test_nested_redaction_is_exact_case_insensitive_and_nonmutating():
    original = {"nested": [{"TOKEN": "secret", "token_count": 3}], "ok": (1, 2)}
    assert redact(original, keys=["token"]) == {
        "nested": [{"TOKEN": "[REDACTED]", "token_count": 3}],
        "ok": [1, 2],
    }
    assert original["nested"][0]["TOKEN"] == "secret"


def test_cycles_depth_width_nodes_and_strings_bounded():
    cyclic = []
    cyclic.append(cyclic)
    assert redact(cyclic, keys=[]) == ["[CYCLE]"]
    assert redact({"a": {"b": 3}}, keys=[], max_depth=1) == {"a": "[DEPTH]"}
    assert redact([1, 2, 3], keys=[], max_items=2) == [1, 2, "[TRUNCATED]"]
    assert redact({"a": 1, "b": 2}, keys=[], max_items=1) == {"a": 1, "[TRUNCATED]": True}
    assert redact([1, [2, 3]], keys=[], max_nodes=2) == [1, "[BUDGET]"]
    assert redact("abcdef", keys=[], max_string=3) == "abc[TRUNCATED]"


def test_hostile_objects_keys_and_subclasses_never_execute():
    class Hostile:
        def __str__(self):
            raise AssertionError("str invoked")

        def __repr__(self):
            raise AssertionError("repr invoked")

    class HostileDict(dict):
        def items(self):
            raise AssertionError("items invoked")

    class HostileString(str):
        def lower(self):
            raise AssertionError("lower invoked")

    value = {
        Hostile(): "dropped",
        "obj": Hostile(),
        "sub": HostileDict(),
        "string": HostileString("secret"),
    }
    assert redact(value, keys=[]) == {"obj": "[OPAQUE]", "sub": "[OPAQUE]", "string": "[OPAQUE]"}


@pytest.mark.parametrize("limit", ["max_depth", "max_items", "max_nodes", "max_string"])
@pytest.mark.parametrize("value", [-1, 0, True, 1.5])
def test_limits_are_positive_integers(limit, value):
    with pytest.raises((TypeError, ValueError)):
        redact({}, keys=[], **{limit: value})


def test_excessive_depth_rejected():
    with pytest.raises(ValueError):
        redact({}, keys=[], max_depth=101)


def test_oversized_keys_are_omitted_instead_of_renamed():
    assert redact(
        {"token_long": "private", "token": "private", "ok": 1}, keys=["token"], max_string=5
    ) == {"token": "[REDA[TRUNCATED]", "ok": 1}


def test_bare_string_redaction_keys_rejected():
    with pytest.raises(TypeError, match="collection"):
        redact({"password": "private"}, keys="password")
