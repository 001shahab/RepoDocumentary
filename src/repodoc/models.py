"""Immutable data models shared across the pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class FileChange:
    """Line statistics for one file in one commit."""

    path: str
    insertions: int
    deletions: int
    binary: bool = False


@dataclass(frozen=True, slots=True)
class Commit:
    """A single commit as read from ``git log``."""

    sha: str
    author_name: str
    author_email: str
    authored_at: datetime
    parents: tuple[str, ...]
    subject: str
    body: str = ""
    changes: tuple[FileChange, ...] = ()

    @property
    def short_sha(self) -> str:
        return self.sha[:7]

    @property
    def insertions(self) -> int:
        return sum(change.insertions for change in self.changes)

    @property
    def deletions(self) -> int:
        return sum(change.deletions for change in self.changes)

    @property
    def churn(self) -> int:
        return self.insertions + self.deletions

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1

    @property
    def author_key(self) -> str:
        """Stable identity used to group commits by person."""
        return (self.author_email or self.author_name).strip().lower()


@dataclass(frozen=True, slots=True)
class Tag:
    """A git tag, typically a release."""

    name: str
    sha: str
    created_at: datetime | None


@dataclass(frozen=True, slots=True)
class Overview:
    """Headline numbers for the whole history."""

    name: str
    first_commit_at: datetime
    last_commit_at: datetime
    span_days: int
    total_commits: int
    merge_commits: int
    contributors: int
    insertions: int
    deletions: int
    files_touched: int
    languages: tuple[str, ...]
    tags: int


@dataclass(frozen=True, slots=True)
class Contributor:
    """Aggregated activity of one person. Email addresses are never stored."""

    name: str
    commits: int
    share: float
    first_commit_at: datetime
    last_commit_at: datetime
    insertions: int
    deletions: int
    role: str


@dataclass(frozen=True, slots=True)
class Moment:
    """A notable event in the history, the raw material for a scene."""

    kind: str
    title: str
    detail: str
    at: datetime | None = None
    sha: str | None = None
    author: str | None = None


@dataclass(frozen=True, slots=True)
class Act:
    """A contiguous chapter of the history."""

    number: int
    start: datetime
    end: datetime
    commits: int
    insertions: int
    deletions: int
    lead_contributors: tuple[str, ...]
    hot_paths: tuple[str, ...]
    highlights: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Dossier:
    """Everything the narrator is allowed to know. Facts only, no prose."""

    overview: Overview
    contributors: tuple[Contributor, ...]
    moments: tuple[Moment, ...]
    acts: tuple[Act, ...]
    vocabulary: tuple[str, ...]
    releases: tuple[Tag, ...] = field(default=())

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation (datetimes as ISO 8601)."""
        data: dict[str, Any] = _jsonable(asdict(self))
        return data


@dataclass(frozen=True, slots=True)
class Narration:
    """The finished script plus provenance information."""

    title: str
    script: str
    style: str
    narrator: str
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = _jsonable(asdict(self))
        return data


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    return value
