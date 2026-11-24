from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from repodoc.analysis import AnalysisOptions, build_dossier, format_span, is_bot
from repodoc.git import GitRepository
from repodoc.models import Commit, Dossier


def _dossier(repo: Path, **options: object) -> Dossier:
    git = GitRepository(repo)
    return build_dossier(
        git.commits(),
        name=git.name,
        tags=git.tags(),
        options=AnalysisOptions(**options),  # type: ignore[arg-type]
    )


def test_overview(story_repo: Path) -> None:
    overview = _dossier(story_repo).overview
    assert overview.total_commits == 8
    assert overview.contributors == 2
    assert overview.tags == 1
    assert overview.span_days == 243
    assert overview.languages[0] == "Python"


def test_contributor_roles(story_repo: Path) -> None:
    people = {person.name: person for person in _dossier(story_repo).contributors}
    assert people["Ada Lovelace"].role == "founder"
    assert people["Alan Turing"].role == "departed"
    assert people["Ada Lovelace"].commits == 5
    assert people["Ada Lovelace"].share == pytest.approx(0.625)


def test_moments(story_repo: Path) -> None:
    kinds = {moment.kind: moment for moment in _dossier(story_repo).moments}
    assert {"genesis", "biggest_change", "great_purge", "long_silence", "busiest_day"} <= set(kinds)
    assert {"night_owl", "firefighting", "departure", "latest"} <= set(kinds)
    assert "Initial commit" in kinds["genesis"].detail
    assert "Remove legacy engine" in kinds["great_purge"].detail
    assert "03:12" in kinds["night_owl"].detail
    assert "hotfix" in kinds["firefighting"].detail


def test_acts_cover_every_commit(story_repo: Path) -> None:
    dossier = _dossier(story_repo, acts=3)
    assert len(dossier.acts) == 3
    assert sum(act.commits for act in dossier.acts) == 8
    assert [act.number for act in dossier.acts] == [1, 2, 3]
    assert all(act.highlights for act in dossier.acts)


def test_acts_shrink_for_tiny_histories(story_repo: Path) -> None:
    git = GitRepository(story_repo)
    commits = git.commits()[:2]
    dossier = build_dossier(commits, name="tiny", options=AnalysisOptions(acts=5))
    assert len(dossier.acts) == 1


def test_anonymize_hides_names(story_repo: Path) -> None:
    payload = json.dumps(_dossier(story_repo, anonymize=True).to_dict())
    assert "Ada" not in payload
    assert "Alan" not in payload
    assert "Contributor A" in payload
    assert "Contributor B" in payload


def test_emails_never_reach_the_dossier(story_repo: Path) -> None:
    payload = json.dumps(_dossier(story_repo).to_dict())
    assert "@example.com" not in payload


def test_vocabulary(story_repo: Path) -> None:
    assert _dossier(story_repo).vocabulary[0] == "engine"


def test_dossier_is_json_serialisable(story_repo: Path) -> None:
    data = _dossier(story_repo).to_dict()
    assert json.loads(json.dumps(data))["overview"]["name"] == "project"


def test_single_commit() -> None:
    commit = Commit(
        sha="a" * 40,
        author_name="Solo",
        author_email="solo@example.com",
        authored_at=datetime(2024, 5, 1, 12, tzinfo=timezone.utc),
        parents=(),
        subject="Hello world",
    )
    dossier = build_dossier([commit], name="solo")
    assert dossier.overview.total_commits == 1
    assert [moment.kind for moment in dossier.moments] == ["genesis", "latest"]


def test_requires_commits() -> None:
    with pytest.raises(ValueError):
        build_dossier([], name="nothing")


@pytest.mark.parametrize(
    ("days", "expected"),
    [(0, "0 days"), (1, "1 day"), (45, "1 month"), (400, "1 year, 1 month"), (730, "2 years")],
)
def test_format_span(days: int, expected: str) -> None:
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    assert format_span(start, start + timedelta(days=days)) == expected


@pytest.mark.parametrize(
    ("name", "email", "expected"),
    [
        ("dependabot[bot]", "49699333+dependabot[bot]@users.noreply.github.com", True),
        ("pre-commit-ci[bot]", "x@y", True),
        ("github-actions", "41898282+github-actions[bot]@users.noreply.github.com", True),
        ("Renovate Bot", "bot@renovateapp.com", True),
        ("Abbott Costello", "abbott@example.com", False),
        ("Ada Lovelace", "ada@example.com", False),
    ],
)
def test_is_bot(name: str, email: str, expected: bool) -> None:
    assert is_bot(name, email) is expected


def test_bots_get_their_own_role_and_moment(story_repo: Path) -> None:
    git = GitRepository(story_repo)
    commits = git.commits()
    robot = replace(commits[-1], sha="b" * 40, author_name="dependabot[bot]", author_email="d@b")
    dossier = build_dossier([*commits, robot], name="project")
    roles = {person.name: person.role for person in dossier.contributors}
    assert roles["dependabot[bot]"] == "bot"
    assert any(moment.kind == "the_machines" for moment in dossier.moments)
