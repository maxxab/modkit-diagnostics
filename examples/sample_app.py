"""An unrelated reading-list application using only public APIs and stdlib."""

import logging

from modkit_diagnostics import (
    DiagnosticError,
    ErrorCatalog,
    ErrorDefinition,
    bind_context,
    get_context,
    log_diagnostic,
)


def main() -> dict[str, str]:
    missing = ErrorDefinition("BOOK_UNAVAILABLE", "Book unavailable")
    catalog = ErrorCatalog([missing], fallback=ErrorDefinition("FAILED", "Please try again"))
    logger = logging.Logger("reading-list")
    logger.propagate = False  # Configuration belongs to this application.
    logger.addHandler(logging.NullHandler())
    with bind_context(request_id="reading-list-1"):
        assert get_context() == {"request_id": "reading-list-1"}
        try:
            raise DiagnosticError("BOOK_UNAVAILABLE", details={"access_token": "example-only"})
        except DiagnosticError as error:
            log_diagnostic(logger, error, catalog=catalog, redact_keys=["access_token"])
            public = catalog.public(error)
    assert get_context() == {}
    assert public == {"code": "BOOK_UNAVAILABLE", "message": "Book unavailable"}
    return public


if __name__ == "__main__":
    print(main())
