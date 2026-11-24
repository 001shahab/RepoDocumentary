"""Runtime settings, read from the environment and an optional ``.env`` file."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_REASONING_EFFORT = "low"


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuration resolved from environment variables."""

    api_key: str | None
    base_url: str | None
    model: str
    reasoning_effort: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env
        return cls(
            api_key=source.get("OPENAI_API_KEY") or None,
            base_url=source.get("OPENAI_BASE_URL") or None,
            model=source.get("REPODOC_MODEL") or DEFAULT_MODEL,
            reasoning_effort=source.get("REPODOC_REASONING_EFFORT") or DEFAULT_REASONING_EFFORT,
        )


def load_dotenv_files(*directories: Path) -> None:
    """Load ``.env`` from the current directory and any *directories* given.

    Existing environment variables always win, so a shell ``export`` overrides a file.
    """
    seen: set[Path] = set()
    for directory in (Path.cwd(), *directories):
        candidate = (directory / ".env").resolve()
        if candidate in seen or not candidate.is_file():
            continue
        seen.add(candidate)
        load_dotenv(candidate, override=False)
