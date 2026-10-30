"""Bounded snapshots of plain data, without arbitrary conversion hooks."""

from collections.abc import Collection
from itertools import islice
from typing import TypeAlias

SafeValue: TypeAlias = None | bool | int | float | str | list["SafeValue"] | dict[str, "SafeValue"]


def redact(
    value: object,
    *,
    keys: Collection[str],
    replacement: str = "[REDACTED]",
    max_depth: int = 10,
    max_items: int = 100,
    max_nodes: int = 1000,
    max_string: int = 4096,
) -> SafeValue:
    """Snapshot exact built-in containers/scalars, redacting exact insensitive keys.

    Unsupported types become ``[OPAQUE]``; non-string or oversized dictionary keys are omitted.
    Limits bound traversal, not the size of the input already allocated by callers.
    Fixed marker strings may exceed max_string. No free-text secret detection.
    """
    for limit in (max_depth, max_items, max_nodes, max_string):
        if type(limit) is not int:
            raise TypeError("limits must be plain integers")
        if limit < 1:
            raise ValueError("limits must be positive")
    if max_depth > 100:
        raise ValueError("max_depth must be at most 100")
    if type(replacement) is not str:
        raise TypeError("replacement must be a plain string")
    if isinstance(keys, (str, bytes)):
        raise TypeError("keys must be a collection of strings, not a bare string")
    if any(type(key) is not str for key in keys):
        raise TypeError("redaction keys must be plain strings")
    sensitive = {key.lower() for key in keys}
    active: set[int] = set()
    remaining = max_nodes

    def clip(text: str) -> str:
        return text if len(text) <= max_string else text[:max_string] + "[TRUNCATED]"

    def visit(item: object, depth: int) -> SafeValue:
        nonlocal remaining
        if remaining <= 0:
            return "[BUDGET]"
        remaining -= 1
        kind = type(item)
        if kind in (type(None), bool, int, float):
            return item  # type: ignore[return-value]
        if kind is str:
            return clip(item)  # type: ignore[arg-type]
        if kind not in (dict, list, tuple):
            return "[OPAQUE]"
        if id(item) in active:
            return "[CYCLE]"
        if depth >= max_depth:
            return "[DEPTH]"
        active.add(id(item))
        try:
            if isinstance(item, dict):
                result: dict[str, SafeValue] = {}
                for key, child in islice(item.items(), max_items):
                    if remaining <= 0:
                        result["[BUDGET]"] = True
                        break
                    if type(key) is not str or len(key) > max_string:
                        remaining -= 1
                        continue
                    if key.lower() in sensitive:
                        remaining -= 1
                        result[key] = clip(replacement)
                    else:
                        result[key] = visit(child, depth + 1)
                if len(item) > max_items:
                    result["[TRUNCATED]"] = True
                return result
            sequence: list[SafeValue] = []
            assert isinstance(item, (list, tuple))
            for child in islice(item, max_items):
                if remaining <= 0:
                    sequence.append("[BUDGET]")
                    break
                sequence.append(visit(child, depth + 1))
            if len(item) > max_items:
                sequence.append("[TRUNCATED]")
            return sequence
        finally:
            active.remove(id(item))

    return visit(value, 0)
