"""The narrator interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from repodoc.models import Narration
from repodoc.prompt import NarrationRequest


@runtime_checkable
class Narrator(Protocol):
    """Anything that can turn a :class:`NarrationRequest` into a :class:`Narration`."""

    name: str

    def narrate(self, request: NarrationRequest) -> Narration:
        """Write the script for *request*."""
        ...


def extract_title(script: str, fallback: str) -> str:
    """Return the first Markdown H1 of *script*, or *fallback*."""
    for line in script.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback
    return fallback
