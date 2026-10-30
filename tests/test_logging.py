import importlib
import logging

import pytest


class RecordingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def api():
    module = importlib.import_module("modkit_diagnostics")
    assert hasattr(module, "log_diagnostic"), "explicit logging API missing"
    return module


def test_explicit_log_redacts_context_details_and_excludes_traceback():
    m = api()
    definition = m.ErrorDefinition("MISSING", "Item unavailable")
    catalog = m.ErrorCatalog([definition], fallback=definition)
    logger = logging.Logger("sample", logging.DEBUG)
    logger.propagate = False
    handler = RecordingHandler()
    logger.addHandler(handler)
    with m.bind_context(token="private", nested={"password": "private"}):
        error = m.DiagnosticError("MISSING", details={"TOKEN": "private", "count": 2})
        error.__cause__ = RuntimeError("secret cause")
        m.log_diagnostic(logger, error, catalog=catalog, redact_keys=["token", "password"])
    assert len(handler.records) == 1
    record = handler.records[0]
    assert record.getMessage() == "Item unavailable"
    assert record.diagnostic == {
        "code": "MISSING",
        "message": "Item unavailable",
        "context": {"token": "[REDACTED]", "nested": {"password": "[REDACTED]"}},
        "details": {"TOKEN": "[REDACTED]", "count": 2},
    }
    assert record.exc_info is None and record.stack_info is None


def test_one_call_per_invocation_no_global_configuration_or_suppression():
    m = api()

    class CountingLogger(logging.Logger):
        def __init__(self):
            super().__init__("count")
            self.calls = 0

        def log(self, *args, **kwargs):
            self.calls += 1
            super().log(*args, **kwargs)

    logger = CountingLogger()
    logger.propagate = True
    parent = logging.Logger("parent")
    logger.parent = parent
    local, ancestor = RecordingHandler(), RecordingHandler()
    logger.addHandler(local)
    parent.addHandler(ancestor)
    root = logging.getLogger()
    before = (root.handlers[:], root.level, root.propagate)
    fallback = m.ErrorDefinition("UNKNOWN", "Safe fallback")
    error = m.DiagnosticError("unrecognized")
    for _ in range(2):
        m.log_diagnostic(
            logger, error, catalog=m.ErrorCatalog([], fallback=fallback), redact_keys=[]
        )
    assert logger.calls == 2
    assert len(local.records) == len(ancestor.records) == 2
    assert local.records[0].diagnostic["code"] == "UNKNOWN"
    assert local.records[0].getMessage() == "Safe fallback"
    assert before == (root.handlers, root.level, root.propagate)
    assert logger.propagate is True


def test_handler_failure_propagates_without_retry():
    m = api()

    class BrokenHandler(logging.Handler):
        calls = 0

        def emit(self, record):
            self.calls += 1
            raise RuntimeError("sink failed")

    logger = logging.Logger("broken")
    handler = BrokenHandler()
    logger.addHandler(handler)
    fallback = m.ErrorDefinition("X", "Safe")
    with pytest.raises(RuntimeError, match="sink failed"):
        m.log_diagnostic(
            logger,
            m.DiagnosticError("X"),
            catalog=m.ErrorCatalog([], fallback=fallback),
            redact_keys=[],
        )
    assert handler.calls == 1


def test_logger_failure_propagates_without_retry():
    m = api()

    class BrokenLogger(logging.Logger):
        calls = 0

        def log(self, *args, **kwargs):
            self.calls += 1
            raise ValueError("logger failed")

    logger = BrokenLogger("broken")
    fallback = m.ErrorDefinition("X", "Safe")
    with pytest.raises(ValueError, match="logger failed"):
        m.log_diagnostic(
            logger,
            m.DiagnosticError("X"),
            catalog=m.ErrorCatalog([], fallback=fallback),
            redact_keys=[],
        )
    assert logger.calls == 1


def test_bare_string_redaction_keys_fail_before_logging():
    m = api()
    logger = logging.Logger("invalid-configuration")
    handler = RecordingHandler()
    logger.addHandler(handler)
    fallback = m.ErrorDefinition("X", "Safe")
    with pytest.raises(TypeError, match="collection"):
        m.log_diagnostic(
            logger,
            m.DiagnosticError("X", details={"password": "private"}),
            catalog=m.ErrorCatalog([], fallback=fallback),
            redact_keys="password",
        )
    assert handler.records == []
