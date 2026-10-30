"""Async-task-local context with bounded copy-in/copy-out snapshots."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from .redaction import SafeValue, redact

_context: ContextVar[dict[str, SafeValue] | None] = ContextVar("modkit_diagnostics", default=None)


def get_context() -> dict[str, SafeValue]:
    """Return an independent bounded snapshot of the current context."""
    result = redact(_context.get() or {}, keys=())
    assert isinstance(result, dict)
    return result


@contextmanager
def bind_context(**fields: object) -> Iterator[None]:
    """Merge a bounded snapshot for this scope and restore even on failure."""
    merged: dict[str, object] = {**get_context(), **fields}
    snapshot = redact(merged, keys=())
    assert isinstance(snapshot, dict)
    token = _context.set(snapshot)
    try:
        yield
    finally:
        _context.reset(token)
