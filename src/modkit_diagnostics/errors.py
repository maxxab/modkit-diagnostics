"""Application-owned error identifiers and explicitly public messages."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass


def _text(value: str, name: str) -> None:
    if type(value) is not str:
        raise TypeError(f"{name} must be a plain string")
    if not value.strip():
        raise ValueError(f"{name} must not be empty")


@dataclass(frozen=True, slots=True)
class ErrorDefinition:
    """A code/message pair explicitly approved by the application for public use."""

    code: str
    message: str

    def __post_init__(self) -> None:
        _text(self.code, "code")
        _text(self.message, "message")


class DiagnosticError(Exception):
    """An error identifier with debug-only details; construction never logs.

    Details are retained by reference until explicit logging snapshots them.
    They are never included in public payloads or this exception's text.
    """

    def __init__(self, code: str, *, details: Mapping[str, object] | None = None) -> None:
        _text(code, "code")
        super().__init__(code)
        self.code = code
        self.details = details if details is not None else {}


class ErrorCatalog:
    """Resolve caller definitions, using an explicit safe fallback for unknown codes."""

    def __init__(
        self, definitions: Iterable[ErrorDefinition], *, fallback: ErrorDefinition
    ) -> None:
        self._definitions: dict[str, ErrorDefinition] = {}
        for definition in definitions:
            if definition.code in self._definitions:
                raise ValueError("duplicate error code")
            self._definitions[definition.code] = definition
        self._fallback = fallback

    def resolve(self, code: str) -> ErrorDefinition:
        """Return the configured definition; never infer text from an exception."""
        return self._definitions.get(code, self._fallback)

    def public(self, diagnostic: DiagnosticError) -> dict[str, str]:
        """Return only the catalog's public code and message, never debug details."""
        definition = self.resolve(diagnostic.code)
        return {"code": definition.code, "message": definition.message}
