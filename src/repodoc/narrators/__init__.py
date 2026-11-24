"""Narrators turn a dossier into a script."""

from __future__ import annotations

from repodoc.narrators.base import Narrator, extract_title
from repodoc.narrators.offline import OfflineNarrator
from repodoc.narrators.openai_narrator import REASONING_EFFORTS, OpenAINarrator

__all__ = ["REASONING_EFFORTS", "Narrator", "OfflineNarrator", "OpenAINarrator", "extract_title"]
