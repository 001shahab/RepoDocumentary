"""Read commit history from a git repository.

Only metadata and line statistics are read. File contents are never loaded, which keeps
the tool fast on large repositories and means source code never leaves the machine.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from repodoc.errors import EmptyRepositoryError, GitError, NotARepositoryError
from repodoc.models import Commit, FileChange, Tag

_RECORD = "\x1e"
_FIELD = "\x1f"
_LOG_FORMAT = _RECORD + _FIELD.join(["%H", "%an", "%ae", "%aI", "%P", "%s", "%b"]) + _FIELD
_TAG_FORMAT = "%(refname:short)%1f%(objectname)%1f%(creatordate:iso-strict)"

_REMOTE_PATTERN = re.compile(r"^(https?://|ssh://|git://|git@[\w.-]+:)")

# Options that make ``git log`` output deterministic regardless of user configuration.
_STABLE_CONFIG: tuple[str, ...] = (
    "-c",
    "core.quotepath=off",
    "-c",
    "log.showSignature=false",
    "-c",
    "color.ui=never",
)


def is_remote_url(target: str) -> bool:
    """Return ``True`` when *target* looks like a clonable URL rather than a local path."""
    return bool(_REMOTE_PATTERN.match(target.strip()))


def _git_executable() -> str:
    executable = shutil.which("git")
    if executable is None:
        raise GitError("git was not found on PATH. Please install git and try again.")
    return executable


def _run_git(args: Sequence[str], cwd: Path | None = None) -> str:
    command = [_git_executable(), *_STABLE_CONFIG, *args]
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:  # pragma: no cover - extremely unusual
        raise GitError(f"Could not run git: {exc}") from exc
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise GitError(f"git {' '.join(args[:2])} failed: {message}")
    return completed.stdout


@contextmanager
def clone_remote(url: str) -> Iterator[Path]:
    """Clone *url* as a bare repository into a temporary directory.

    A bare clone downloads history without checking out a working tree, which is the
    cheapest way to obtain everything ``git log --numstat`` needs. The directory is
    removed when the context exits.
    """
    with tempfile.TemporaryDirectory(prefix="repodoc-") as tmp:
        destination = Path(tmp) / "repo.git"
        _run_git(["clone", "--bare", "--quiet", url, str(destination)])
        yield destination


class GitRepository:
    """A thin, read-only wrapper around a local git repository."""

    def __init__(self, path: Path | str, *, display_name: str | None = None) -> None:
        self._display_name = display_name
        candidate = Path(path).expanduser().resolve()
        if not candidate.exists():
            raise NotARepositoryError(f"Path does not exist: {candidate}")
        try:
            git_dir = _run_git(["rev-parse", "--absolute-git-dir"], cwd=candidate).strip()
        except GitError as exc:
            raise NotARepositoryError(f"Not a git repository: {candidate}") from exc
        self.path = candidate
        self.git_dir = Path(git_dir)

    def __repr__(self) -> str:
        return f"GitRepository({str(self.path)!r})"

    def _git(self, *args: str) -> str:
        return _run_git(args, cwd=self.path)

    @property
    def name(self) -> str:
        """A human friendly project name, taken from ``origin`` when available."""
        if self._display_name:
            return self._display_name
        try:
            remote = self._git("config", "--get", "remote.origin.url").strip()
        except GitError:
            remote = ""
        source = remote or str(self.path)
        stem = source.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
        stem = stem.removesuffix(".git")
        if stem in {"", "repo"}:
            stem = self.path.name.removesuffix(".git")
        return stem or "repository"

    def has_commits(self) -> bool:
        try:
            self._git("rev-parse", "--verify", "--quiet", "HEAD")
        except GitError:
            return False
        return True

    def commits(
        self,
        rev: str = "HEAD",
        *,
        since: str | None = None,
        until: str | None = None,
        max_commits: int | None = None,
        include_merges: bool = True,
    ) -> list[Commit]:
        """Return commits reachable from *rev*, oldest first.

        ``max_commits`` keeps the most recent *n* commits, mirroring ``git log -n``.
        ``since`` and ``until`` accept anything git understands, such as ``"2 years ago"``.
        """
        if not self.has_commits():
            raise EmptyRepositoryError("This repository has no commits yet.")
        args = ["log", f"--format={_LOG_FORMAT}", "--numstat", "--no-renames", "--date-order"]
        if since:
            args.append(f"--since={since}")
        if until:
            args.append(f"--until={until}")
        if max_commits is not None:
            if max_commits < 1:
                raise ValueError("max_commits must be a positive integer")
            args.append(f"--max-count={max_commits}")
        if not include_merges:
            args.append("--no-merges")
        args.extend([rev, "--"])
        commits = parse_log(self._git(*args))
        if not commits:
            raise EmptyRepositoryError("No commits match the selected range.")
        commits.reverse()
        return commits

    def tags(self) -> list[Tag]:
        """Return tags sorted by creation date, oldest first."""
        output = self._git("for-each-ref", f"--format={_TAG_FORMAT}", "refs/tags")
        tags: list[Tag] = []
        for line in output.splitlines():
            parts = line.split(_FIELD)
            if len(parts) != 3 or not parts[0]:
                continue
            name, sha, created = parts
            tags.append(Tag(name=name, sha=sha, created_at=_parse_date(created)))
        tags.sort(key=lambda tag: (tag.created_at is None, tag.created_at or datetime.min))
        return tags


def parse_log(output: str) -> list[Commit]:
    """Parse the output of ``git log`` produced with :data:`_LOG_FORMAT` and ``--numstat``.

    Commits are returned in the order git printed them (newest first by default).
    """
    commits: list[Commit] = []
    for record in output.split(_RECORD):
        if not record.strip():
            continue
        fields = record.split(_FIELD)
        if len(fields) < 8:
            continue
        sha, name, email, date, parents, subject, body, numstat = (
            fields[0],
            fields[1],
            fields[2],
            fields[3],
            fields[4],
            fields[5],
            _FIELD.join(fields[6:-1]),
            fields[-1],
        )
        authored_at = _parse_date(date)
        if authored_at is None:
            continue
        commits.append(
            Commit(
                sha=sha.strip(),
                author_name=name.strip() or "Unknown",
                author_email=email.strip(),
                authored_at=authored_at,
                parents=tuple(parents.split()),
                subject=subject.strip(),
                body=body.strip(),
                changes=tuple(_parse_numstat(numstat)),
            )
        )
    return commits


def _parse_numstat(block: str) -> Iterator[FileChange]:
    for line in block.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        added, removed, path = parts
        if added == "-" or removed == "-":
            yield FileChange(path=path, insertions=0, deletions=0, binary=True)
            continue
        try:
            yield FileChange(path=path, insertions=int(added), deletions=int(removed))
        except ValueError:
            continue


def _parse_date(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
