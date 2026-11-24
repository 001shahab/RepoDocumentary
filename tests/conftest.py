"""Shared fixtures: build small, fully deterministic git repositories on the fly."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass(frozen=True)
class FakeCommit:
    message: str
    author: str
    email: str
    date: str
    files: dict[str, str]


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


@pytest.fixture(autouse=True)
def _isolated_git(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Keep the developer's global git configuration out of the tests."""
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(home / ".gitconfig"))
    for variable in (
        "OPENAI_API_KEY",
        "REPODOC_MODEL",
        "REPODOC_REASONING_EFFORT",
        "XDG_CONFIG_HOME",
    ):
        # setenv first so monkeypatch restores the variable even if load_dotenv sets it later.
        monkeypatch.setenv(variable, "")
        monkeypatch.delenv(variable)


@pytest.fixture
def make_repo(tmp_path: Path) -> Callable[[list[FakeCommit]], Path]:
    def factory(commits: list[FakeCommit]) -> Path:
        repo = tmp_path / "project"
        repo.mkdir()
        _git(repo, "init", "--quiet", "--initial-branch=main")
        _git(repo, "config", "commit.gpgsign", "false")
        _git(repo, "config", "tag.gpgsign", "false")
        _git(repo, "config", "user.name", "Test Runner")
        _git(repo, "config", "user.email", "runner@example.com")
        for commit in commits:
            for name, content in commit.files.items():
                path = repo / name
                if content == "<delete>":
                    path.unlink()
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            _git(repo, "add", "--all")
            env = {
                "GIT_AUTHOR_NAME": commit.author,
                "GIT_AUTHOR_EMAIL": commit.email,
                "GIT_AUTHOR_DATE": commit.date,
                "GIT_COMMITTER_NAME": commit.author,
                "GIT_COMMITTER_EMAIL": commit.email,
                "GIT_COMMITTER_DATE": commit.date,
            }
            _git(repo, "commit", "--quiet", "--allow-empty", "-m", commit.message, env=env)
        return repo

    return factory


def lines(count: int, prefix: str = "line") -> str:
    return "".join(f"{prefix} {index}\n" for index in range(count))


@pytest.fixture
def story_repo(make_repo: Callable[[list[FakeCommit]], Path]) -> Path:
    """A small history with a founder, a newcomer who leaves, a purge and a late night."""
    ada = ("Ada Lovelace", "ada@example.com")
    alan = ("Alan Turing", "alan@example.com")
    history = [
        FakeCommit("Initial commit", *ada, "2023-01-02T10:00:00+02:00", {"README.md": "hi\n"}),
        FakeCommit(
            "Add engine core",
            *ada,
            "2023-01-03T11:00:00+02:00",
            {"src/engine.py": lines(200), "src/util.py": lines(20)},
        ),
        FakeCommit(
            "Add tests for engine", *alan, "2023-01-04T12:00:00+02:00", {"tests/t.py": lines(30)}
        ),
        FakeCommit(
            "hotfix: engine crashes on empty input",
            *alan,
            "2023-01-04T03:12:00+02:00",
            {"src/engine.py": lines(195) + "fixed\n"},
        ),
        FakeCommit("Refactor util", *alan, "2023-01-04T15:00:00+02:00", {"src/util.py": lines(25)}),
        FakeCommit(
            "Remove legacy engine",
            *ada,
            "2023-09-01T09:00:00+02:00",
            {"src/engine.py": "<delete>", "src/core.py": lines(10)},
        ),
        FakeCommit(
            "Release engine v1", *ada, "2023-09-02T09:00:00+02:00", {"CHANGELOG.md": "v1\n"}
        ),
        FakeCommit(
            "Polish engine docs", *ada, "2023-09-03T09:00:00+02:00", {"README.md": "docs\n"}
        ),
    ]
    repo = make_repo(history)
    _git(repo, "tag", "-a", "v1.0.0", "-m", "First release")
    return repo
