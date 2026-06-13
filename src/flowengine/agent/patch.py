"""Minimal RFC-6902 JSON Patch application (no external dependency).

Agents are excellent at emitting JSON Patch operations; :func:`apply_patch` lets
FlowEngine consume the very repair hints it produces, closing the
validate → repair → revalidate loop without a third-party library.

Supports the ``add``, ``replace``, and ``remove`` operations against dicts and
lists addressed by JSON Pointer (RFC-6901), including the ``-`` end-of-array token.
"""

from __future__ import annotations

import copy
from typing import Any


class JsonPatchError(ValueError):
    """Raised when a patch operation cannot be applied."""


def _unescape(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _split_pointer(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise JsonPatchError(f"Invalid JSON Pointer: {pointer!r}")
    return [_unescape(tok) for tok in pointer.split("/")[1:]]


def _resolve_parent(doc: Any, tokens: list[str]) -> tuple[Any, str]:
    """Return (container, last_key) for the parent of the target location."""
    current = doc
    for tok in tokens[:-1]:
        if isinstance(current, list):
            current = current[int(tok)]
        elif isinstance(current, dict):
            current = current[tok]
        else:
            raise JsonPatchError(f"Path traverses non-container at {tok!r}")
    return current, tokens[-1]


def _apply_one(doc: Any, op: dict[str, Any]) -> Any:
    operation = op.get("op")
    pointer = op.get("path", "")
    tokens = _split_pointer(pointer)

    if not tokens:
        # Whole-document replace.
        if operation in ("add", "replace"):
            return copy.deepcopy(op.get("value"))
        raise JsonPatchError(f"Cannot '{operation}' the whole document")

    container, key = _resolve_parent(doc, tokens)

    if operation in ("add", "replace"):
        value = copy.deepcopy(op.get("value"))
        if isinstance(container, list):
            idx = len(container) if key == "-" else int(key)
            if operation == "add":
                container.insert(idx, value)
            else:
                container[idx] = value
        elif isinstance(container, dict):
            container[key] = value
        else:
            raise JsonPatchError(f"Cannot set on non-container at {pointer!r}")
    elif operation == "remove":
        if isinstance(container, list):
            del container[int(key)]
        elif isinstance(container, dict):
            container.pop(key, None)
        else:
            raise JsonPatchError(f"Cannot remove from non-container at {pointer!r}")
    else:
        raise JsonPatchError(f"Unsupported op: {operation!r}")
    return doc


def apply_patch(document: Any, patch: list[dict[str, Any]]) -> Any:
    """Apply a list of JSON Patch operations, returning a new document.

    The input ``document`` is not mutated.
    """
    result = copy.deepcopy(document)
    for op in patch:
        result = _apply_one(result, op)
    return result
