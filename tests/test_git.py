from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from repodoc.errors import EmptyRepositoryError, NotARepositoryError
from repodoc.git import GitRepository, is_remote_url, parse_log

from .conftest import FakeCommit


def test_reads_commits_oldest_first(story_repo: Path) -> None:
    commits = GitRepository(story_repo).commits()
    assert len(commits) == 8
    assert commits[0].subject == "Initial commit"
    assert commits[-1].subject == "Polish engine docs"
    assert commits[1].insertions == 220
    assert {change.path for change in commits[1].changes} == {"src/engine.py", "src/util.py"}


def test_deletions_are_counted(story_repo: Path) -> None:
    purge = next(c for c in GitRepository(story_repo).commits() if c.subject.startswith("Remove"))
    assert purge.deletions == 196
    assert purge.insertions == 10


def test_max_commits_keeps_most_recent(story_repo: Path) -> None:
    commits = GitRepository(story_repo).commits(max_commits=2)
    assert [commit.subject for commit in commits] == ["Release engine v1", "Polish engine docs"]


def test_since_filter(story_repo: Path) -> None:
    commits = GitRepository(story_repo).commits(since="2023-08-01")
    assert len(commits) == 3


def test_tags(story_repo: Path) -> None:
    tags = GitRepository(story_repo).tags()
    assert [tag.name for tag in tags] == ["v1.0.0"]
    assert tags[0].created_at is not None


def test_name_falls_back_to_directory(story_repo: Path) -> None:
    assert GitRepository(story_repo).name == "project"


def test_display_name_override(story_repo: Path) -> None:
    assert GitRepository(story_repo, display_name="Rocket").name == "Rocket"


def test_not_a_repository(tmp_path: Path) -> None:
    with pytest.raises(NotARepositoryError):
        GitRepository(tmp_path)


def test_missing_path(tmp_path: Path) -> None:
    with pytest.raises(NotARepositoryError):
        GitRepository(tmp_path / "nope")


def test_empty_repository(make_repo: Callable[[list[FakeCommit]], Path]) -> None:
    repo = make_repo([])
    with pytest.raises(EmptyRepositoryError):
        GitRepository(repo).commits()


def test_parse_log_handles_binary_and_bad_records() -> None:
    record = (
        "\x1eabc123\x1fAda\x1fada@x\x1f2024-01-01T00:00:00+00:00\x1f\x1fsubject\x1fbody\x1f\n"
        "-\t-\timage.png\n3\t1\tcode.py\nnot a numstat line\n"
        "\x1egarbage"
    )
    commits = parse_log(record)
    assert len(commits) == 1
    commit = commits[0]
    assert commit.body == "body"
    assert commit.changes[0].binary
    assert commit.insertions == 3
    assert commit.deletions == 1


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("https://github.com/001shahab/RepoDocumentary", True),
        ("git@github.com:001shahab/RepoDocumentary.git", True),
        ("ssh://git@example.com/repo.git", True),
        (".", False),
        ("~/code/app", False),
        ("C:\\code\\app", False),
    ],
)
def test_is_remote_url(target: str, expected: bool) -> None:
    assert is_remote_url(target) is expected
