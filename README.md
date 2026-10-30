# modkit-diagnostics

Application-owned errors, bounded task-local context and explicit structured logging.
**Python 3.12+, MIT, zero runtime dependencies.** No framework integration required.

```sh
pip install modkit-diagnostics
```

## Small public API

```python
import logging
from modkit_diagnostics import (
    DiagnosticError, ErrorCatalog, ErrorDefinition,
    bind_context, get_context, log_diagnostic, redact,
)

catalog = ErrorCatalog(
    [ErrorDefinition("BOOK_UNAVAILABLE", "Book unavailable")],
    fallback=ErrorDefinition("FAILED", "Please try again"),
)
logger = logging.getLogger("reading-list")  # Configure handlers in your app.
with bind_context(request_id="reading-list-1"):
    error = DiagnosticError("BOOK_UNAVAILABLE", details={"token": "example-only"})
    log_diagnostic(logger, error, catalog=catalog, redact_keys=["token"])
    public = catalog.public(error)
assert public == {"code": "BOOK_UNAVAILABLE", "message": "Book unavailable"}
assert get_context() == {}
```

- `ErrorDefinition(code, message)` is immutable; nonempty plain strings required.
- `ErrorCatalog(definitions, *, fallback)` rejects duplicate codes. `resolve(code)`
  returns a configured definition or the fallback. `public(error)` creates a new
  **code/message-only** dictionary. Applications must supply public-safe messages.
- `DiagnosticError(code, *, details=None)` does not log. Details are debug-only,
  retained by reference until explicit logging snapshots them; do not mutate them
  concurrently. Its text contains the supplied code only. Catalog output never
  includes the unknown code, exception cause, traceback or details.
- `bind_context(**fields)` snapshots and merges fields for a scope, then restores
  the previous context even on exceptions. `get_context()` returns an independent
  snapshot. ContextVars isolate asyncio tasks; child tasks inherit their starting
  context. New threads need explicit context propagation if desired.
- `log_diagnostic(logger, error, *, catalog, redact_keys, level=logging.ERROR)`
  calls the provided standard logger's `log` **once per invocation**. Record message
  is the catalog message; `record.diagnostic` contains public `code`/`message` plus
  debug-only `context`/`details`. No automatic deduplication: calling twice logs twice.
  Filtering, disabled logging, handlers and propagation can produce zero or many
  outputs. The library does not install handlers or alter global logging state.
  Logger/handler failures follow stdlib/application behavior; this helper does not
  swallow exceptions, retry, or log its own failure. A handler may itself swallow
  failures. Exceptions and catalogs do not need configured logging.

## Snapshot and redaction boundaries

`redact(value, *, keys, replacement="[REDACTED]", max_depth=10, max_items=100,
max_nodes=1000, max_string=4096)` creates a new safe snapshot. Keys match exactly,
case-insensitively, at every nested dictionary. Supply a collection such as `["token"]`,
not a bare string (which raises TypeError before logging). This is **not secret detection**:
free text, catalog messages, and values under unmatched keys can still contain secrets.
Debug data should never be sent to clients simply because it was redacted.

Only exact built-in dict/list/tuple and None/bool/int/float/str values are supported.
Tuples become lists; custom objects and subclasses become `[OPAQUE]` without invoking
`str`, `repr`, serialization, deepcopy or iteration hooks. Non-string and oversized
keys are omitted rather than renamed. No custom mapping adapter is invoked. Cycles
become `[CYCLE]`; deep containers `[DEPTH]`; exhausted node budget `[BUDGET]`.
Long strings keep a prefix plus `[TRUNCATED]`; collection width truncation adds that
marker (dictionary marker value is `True`). Dictionary budget markers use `True`.
Marker names may collide with application keys and are reserved for diagnostics.
Shared noncyclic containers are copied independently. All limits must be positive
plain integers, max_depth at most 100. Fixed markers can exceed max_string. Numeric
scalars are retained unchanged. Limits bound traversal of plain values, not memory
already allocated by callers or application-provided configuration collections.

Context snapshots use the defaults. Log snapshots use the defaults plus supplied
redact_keys. This deliberately lossy diagnostic representation is not a data storage,
JSON serializer or general transport format (e.g. nonfinite floats remain floats).
No traceback logging option or automatic exception string extraction is provided.

## Development and compatibility

```sh
python -m venv .venv
# Activate .venv using your platform's normal activation command.
python -m pip install -r requirements-dev.txt
python -m pytest
ruff check src tests scripts examples
mypy src scripts examples
python -m build
python -m twine check dist/*
python scripts/check_wheel.py dist/modkit_diagnostics-0.1.0-py3-none-any.whl
```

The checker creates a fresh venv outside the checkout, installs the exact wheel
non-editably with pytest, verifies origin/version/dependencies, and runs the sample
and copied full behavior suite in Python isolated mode. It requires access to PyPI
for test tooling. CI covers Python 3.12 and 3.14 on Linux, macOS and Windows, including
an sdist rebuild. CI configuration is not evidence that hosted jobs have run.
See [the sample](examples/sample_app.py). No optional adapters or sibling packages.

Version `0.1.0` is an initial SemVer release candidate, not a stability guarantee.
Before 1.0, incompatible public API changes require a minor bump and migration notes;
compatible fixes use patch releases. No release is implied by building locally.
