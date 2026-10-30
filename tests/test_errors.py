import importlib
import logging

import pytest


def api():
    module = importlib.import_module("modkit_diagnostics")
    assert hasattr(module, "ErrorDefinition"), "app-owned catalog API missing"
    return module


def test_custom_and_fallback():
    m = api()
    known = m.ErrorDefinition("BOOK_MISSING", "Book unavailable")
    fallback = m.ErrorDefinition("UNKNOWN", "Please try again")
    catalog = m.ErrorCatalog([known], fallback=fallback)
    assert catalog.resolve("BOOK_MISSING") is known
    assert catalog.resolve("unrecognized") is fallback
    with pytest.raises(AttributeError):
        known.code = "changed"


def test_duplicate_and_invalid_definitions():
    m = api()
    definition = m.ErrorDefinition("X", "Safe")
    with pytest.raises(ValueError, match="duplicate"):
        m.ErrorCatalog([definition, definition], fallback=definition)
    for code, message in [("", "Safe"), ("X", ""), (12, "Safe")]:
        with pytest.raises((ValueError, TypeError)):
            m.ErrorDefinition(code, message)


def test_public_excludes_details_and_cause_and_no_logs(caplog):
    m = api()
    fallback = m.ErrorDefinition("UNKNOWN", "Please try again")
    catalog = m.ErrorCatalog([], fallback=fallback)
    with caplog.at_level(logging.DEBUG):
        try:
            raise ValueError("private upstream password")
        except ValueError as cause:
            error = m.DiagnosticError("unrecognized", details={"debug": "private value"})
            error.__cause__ = cause
        assert catalog.public(error) == {"code": "UNKNOWN", "message": "Please try again"}
        assert "private" not in str(error)
        assert "private" not in repr(error)
    assert caplog.records == []
