"""Small framework-independent diagnostics primitives. No logging configuration."""

from .context import bind_context, get_context
from .errors import DiagnosticError, ErrorCatalog, ErrorDefinition
from .logging import log_diagnostic
from .redaction import redact

__all__ = [
    "DiagnosticError",
    "ErrorCatalog",
    "ErrorDefinition",
    "bind_context",
    "get_context",
    "redact",
    "log_diagnostic",
]
