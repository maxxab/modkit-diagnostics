"""Explicit stdlib logging adapter; applications own handlers and propagation."""

import logging
from collections.abc import Collection

from .context import get_context
from .errors import DiagnosticError, ErrorCatalog
from .redaction import redact


def log_diagnostic(
    logger: logging.Logger,
    diagnostic: DiagnosticError,
    *,
    catalog: ErrorCatalog,
    redact_keys: Collection[str],
    level: int = logging.ERROR,
) -> None:
    """Call logger.log once with a safe message and redacted structured debug data.

    The record's ``diagnostic`` extra field includes public code/message and
    debug-only context/details. Key redaction cannot sanitize free text. No
    cause, traceback, retry, suppression, configuration or exception swallowing.
    A single call may produce zero, one or many outputs per application setup.
    """
    public = catalog.public(diagnostic)
    payload = {
        **public,
        "context": redact(get_context(), keys=redact_keys),
        "details": redact(diagnostic.details, keys=redact_keys),
    }
    logger.log(level, public["message"], extra={"diagnostic": payload})
