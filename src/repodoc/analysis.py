"""Condense a raw commit history into a factual :class:`~repodoc.models.Dossier`.

The dossier is the single source of truth handed to a narrator. Keeping analysis
deterministic and separate from storytelling means the facts can be inspected
(``repodoc --dossier``), tested, and trusted, while the narrator only adds tone.
"""

from __future__ import annotations

import re
import string
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from itertools import pairwise
from pathlib import PurePosixPath

from repodoc.models import Act, Commit, Contributor, Dossier, Moment, Overview, Tag

MAX_CONTRIBUTORS = 12
MAX_HIGHLIGHTS_PER_ACT = 6
MAX_SUBJECT_LENGTH = 120
MIN_PURGE_DELETIONS = 50
MIN_SILENCE_DAYS = 7
MIN_BUSY_DAY_COMMITS = 3
NIGHT_HOURS = range(0, 5)
MIN_DEPARTURE_COMMITS = 3
MAX_DEPARTURES = 4

_BOT = re.compile(
    r"\[bot\]|\bbot\b|dependabot|renovate|github-actions|pre-commit-ci|greenkeeper",
    re.IGNORECASE,
)

_FIREFIGHTING = re.compile(
    r"\b(hot ?fix|urgent|critical|emergency|oops|typo|revert|broke|broken|quick ?fix)\b",
    re.IGNORECASE,
)
_WORD = re.compile(r"[a-zA-Z][a-zA-Z'-]{2,}")

_STOPWORDS = frozenset(
    """
    the and for with from into this that these those are was were has have had not but
    use used using add adds added update updates updated fix fixes fixed remove removes
    removed change changes changed make makes made more less some all any via when then
    than also just only now new old get set its it's out off one two can will should
    merge merged pull request branch main master into onto been being per our your their
    commit commits wip minor small initial misc
    """.split()
)

_LANGUAGES: dict[str, str] = {
    ".py": "Python",
    ".ipynb": "Jupyter",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".c": "C",
    ".h": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".scala": "Scala",
    ".r": "R",
    ".jl": "Julia",
    ".m": "Objective-C or MATLAB",
    ".lua": "Lua",
    ".dart": "Dart",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".hs": "Haskell",
    ".sh": "Shell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".tex": "LaTeX",
    ".md": "Markdown",
}


@dataclass(frozen=True, slots=True)
class AnalysisOptions:
    """Tunable knobs for :func:`build_dossier`."""

    acts: int = 4
    anonymize: bool = False


def build_dossier(
    commits: Sequence[Commit],
    *,
    name: str,
    tags: Sequence[Tag] = (),
    options: AnalysisOptions | None = None,
) -> Dossier:
    """Analyse *commits* (oldest first) and return a :class:`Dossier`."""
    if not commits:
        raise ValueError("build_dossier() needs at least one commit")
    options = options or AnalysisOptions()
    ordered = sorted(commits, key=lambda commit: commit.authored_at)
    names = _display_names(ordered, anonymize=options.anonymize)

    contributors = _contributors(ordered, names)
    return Dossier(
        overview=_overview(ordered, name=name, contributors=len(names), tags=len(tags)),
        contributors=contributors,
        moments=tuple(_moments(ordered, names, contributors)),
        acts=tuple(_acts(ordered, names, options.acts)),
        vocabulary=tuple(_vocabulary(ordered)),
        releases=tuple(tags),
    )


# --------------------------------------------------------------------------- identities


def _display_names(commits: Sequence[Commit], *, anonymize: bool) -> dict[str, str]:
    """Map each author key to the name shown in the story."""
    spellings: dict[str, Counter[str]] = defaultdict(Counter)
    bots: set[str] = set()
    order: list[str] = []
    for commit in commits:
        key = commit.author_key
        if key not in spellings:
            order.append(key)
        spellings[key][commit.author_name] += 1
        if is_bot(commit.author_name, commit.author_email):
            bots.add(key)
    names = {key: spellings[key].most_common(1)[0][0] for key in order}
    if not anonymize:
        return names
    humans = (key for key in order if key not in bots)
    anonymous = {key: f"Contributor {_letter(index)}" for index, key in enumerate(humans)}
    return {key: anonymous.get(key, names[key]) for key in order}


def _letter(index: int) -> str:
    letters = string.ascii_uppercase
    label = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, len(letters))
        label = letters[remainder] + label
    return label


# --------------------------------------------------------------------------- overview


def _overview(commits: Sequence[Commit], *, name: str, contributors: int, tags: int) -> Overview:
    first, last = commits[0].authored_at, commits[-1].authored_at
    files: set[str] = set()
    languages: Counter[str] = Counter()
    for commit in commits:
        for change in commit.changes:
            files.add(change.path)
            language = _LANGUAGES.get(PurePosixPath(change.path).suffix.lower())
            if language:
                languages[language] += change.insertions + change.deletions + 1
    return Overview(
        name=name,
        first_commit_at=first,
        last_commit_at=last,
        span_days=max(0, (last - first).days),
        total_commits=len(commits),
        merge_commits=sum(commit.is_merge for commit in commits),
        contributors=contributors,
        insertions=sum(commit.insertions for commit in commits),
        deletions=sum(commit.deletions for commit in commits),
        files_touched=len(files),
        languages=tuple(language for language, _ in languages.most_common(5)),
        tags=tags,
    )


# --------------------------------------------------------------------------- contributors


def _contributors(commits: Sequence[Commit], names: dict[str, str]) -> tuple[Contributor, ...]:
    grouped: dict[str, list[Commit]] = defaultdict(list)
    for commit in commits:
        grouped[commit.author_key].append(commit)

    end = commits[-1].authored_at
    span = end - commits[0].authored_at
    departure_gap = max(timedelta(days=90), span * 0.2)
    founder = commits[0].author_key
    total = len(commits)

    profiles: list[Contributor] = []
    for key, own in grouped.items():
        if is_bot(own[0].author_name, own[0].author_email):
            role = "bot"
        elif key == founder:
            role = "founder"
        elif end - own[-1].authored_at > departure_gap:
            role = "departed"
        else:
            role = "active"
        profiles.append(
            Contributor(
                name=names[key],
                commits=len(own),
                share=round(len(own) / total, 3),
                first_commit_at=own[0].authored_at,
                last_commit_at=own[-1].authored_at,
                insertions=sum(commit.insertions for commit in own),
                deletions=sum(commit.deletions for commit in own),
                role=role,
            )
        )
    profiles.sort(key=lambda person: (-person.commits, person.first_commit_at))
    return tuple(profiles[:MAX_CONTRIBUTORS])


# --------------------------------------------------------------------------- moments


def _moments(
    commits: Sequence[Commit],
    names: dict[str, str],
    contributors: Sequence[Contributor],
) -> Iterable[Moment]:
    def author(commit: Commit) -> str:
        return names[commit.author_key]

    def moment(kind: str, title: str, detail: str, commit: Commit) -> Moment:
        return Moment(
            kind=kind,
            title=title,
            detail=detail,
            at=commit.authored_at,
            sha=commit.short_sha,
            author=author(commit),
        )

    first = commits[0]
    yield moment(
        "genesis",
        "The first commit",
        f'{author(first)} wrote the first commit: "{_clip(first.subject)}" '
        f"({first.insertions} lines added across {len(first.changes)} files).",
        first,
    )

    authored = [commit for commit in commits if not commit.is_merge and commit.changes]
    if authored:
        biggest = max(authored, key=lambda commit: commit.churn)
        yield moment(
            "biggest_change",
            "The biggest single change",
            f'"{_clip(biggest.subject)}" touched {len(biggest.changes)} files, adding '
            f"{biggest.insertions} and removing {biggest.deletions} lines.",
            biggest,
        )

        purges = [c for c in authored if c.deletions > c.insertions]
        if purges:
            purge = max(purges, key=lambda commit: commit.deletions)
            if purge.deletions >= MIN_PURGE_DELETIONS and purge.sha != biggest.sha:
                yield moment(
                    "great_purge",
                    "The great purge",
                    f'"{_clip(purge.subject)}" deleted {purge.deletions} lines '
                    f"while adding only {purge.insertions}.",
                    purge,
                )

    if len(commits) > 1:
        gaps = pairwise(commits)
        before, after = max(gaps, key=lambda pair: pair[1].authored_at - pair[0].authored_at)
        silence = (after.authored_at - before.authored_at).days
        if silence >= MIN_SILENCE_DAYS:
            yield moment(
                "long_silence",
                "The long silence",
                f"No commits for {silence} days. The quiet ended when {author(after)} "
                f'committed "{_clip(after.subject)}".',
                after,
            )

    per_day: Counter[date] = Counter(commit.authored_at.date() for commit in commits)
    busiest_day, busiest_count = per_day.most_common(1)[0]
    if busiest_count >= MIN_BUSY_DAY_COMMITS:
        that_day = [commit for commit in commits if commit.authored_at.date() == busiest_day]
        cast = sorted({author(commit) for commit in that_day})
        yield Moment(
            kind="busiest_day",
            title="The busiest day",
            detail=f"{busiest_count} commits landed on {busiest_day.isoformat()} by {_join(cast)}.",
            at=that_day[0].authored_at,
        )

    night = [
        commit
        for commit in commits
        if commit.authored_at.hour in NIGHT_HOURS
        and not is_bot(commit.author_name, commit.author_email)
    ]
    if night:
        latest = max(night, key=lambda commit: (commit.authored_at.hour, commit.churn))
        yield moment(
            "night_owl",
            "After midnight",
            f"{len(night)} commits were made between midnight and 5 a.m. (author local time). "
            f'The latest was "{_clip(latest.subject)}" at '
            f"{latest.authored_at.strftime('%H:%M')}.",
            latest,
        )

    bots = [commit for commit in commits if is_bot(commit.author_name, commit.author_email)]
    if bots:
        busiest_bot = Counter(author(commit) for commit in bots).most_common(1)[0][0]
        yield Moment(
            kind="the_machines",
            title="Rise of the machines",
            detail=f"Bots made {len(bots)} commits "
            f"({round(100 * len(bots) / len(commits))}% of all history), "
            f"the most prolific being {busiest_bot}.",
            at=bots[0].authored_at,
            author=busiest_bot,
        )

    humans = [commit for commit in commits if not is_bot(commit.author_name, commit.author_email)]
    weekend = [commit for commit in humans if commit.authored_at.weekday() >= 5]
    if humans and weekend and len(weekend) / len(humans) >= 0.1:
        yield Moment(
            kind="weekend_work",
            title="Weekend shifts",
            detail=f"{len(weekend)} human commits ({round(100 * len(weekend) / len(humans))}%) "
            "were made on a Saturday or Sunday.",
        )

    fires = [commit for commit in commits if _FIREFIGHTING.search(commit.subject)]
    if fires:
        hottest = max(fires, key=lambda commit: commit.churn)
        yield moment(
            "firefighting",
            "Firefighting",
            f"{len(fires)} commit messages mention hotfixes, reverts, typos or breakage. "
            f'The largest was "{_clip(hottest.subject)}".',
            hottest,
        )

    departed = [
        person
        for person in contributors
        if person.role == "departed" and person.commits >= MIN_DEPARTURE_COMMITS
    ]
    for person in departed[:MAX_DEPARTURES]:
        yield Moment(
            kind="departure",
            title=f"{person.name} goes quiet",
            detail=f"{person.name} made {person.commits} commits, then stopped after "
            f"{person.last_commit_at.date().isoformat()}.",
            at=person.last_commit_at,
            author=person.name,
        )

    last = commits[-1]
    yield moment(
        "latest",
        "The latest commit",
        f'The most recent commit is "{_clip(last.subject)}" by {author(last)}.',
        last,
    )


# --------------------------------------------------------------------------- acts


def _acts(commits: Sequence[Commit], names: dict[str, str], requested: int) -> Iterable[Act]:
    count = max(1, min(requested, len(commits) // 2 or 1))
    size, remainder = divmod(len(commits), count)
    start = 0
    for number in range(1, count + 1):
        end = start + size + (1 if number <= remainder else 0)
        chunk = commits[start:end]
        start = end
        if not chunk:
            continue
        leads = Counter(names[commit.author_key] for commit in chunk)
        paths: Counter[str] = Counter()
        for commit in chunk:
            for change in commit.changes:
                paths[_area(change.path)] += change.insertions + change.deletions + 1
        yield Act(
            number=number,
            start=chunk[0].authored_at,
            end=chunk[-1].authored_at,
            commits=len(chunk),
            insertions=sum(commit.insertions for commit in chunk),
            deletions=sum(commit.deletions for commit in chunk),
            lead_contributors=tuple(name for name, _ in leads.most_common(3)),
            hot_paths=tuple(path for path, _ in paths.most_common(3)),
            highlights=tuple(_highlights(chunk)),
        )


def _highlights(chunk: Sequence[Commit]) -> list[str]:
    """Pick representative subjects: the first, the last and the heaviest in between."""
    chosen = {chunk[0].sha, chunk[-1].sha}
    for commit in sorted(chunk, key=lambda c: c.churn, reverse=True):
        if len(chosen) >= MAX_HIGHLIGHTS_PER_ACT:
            break
        if not commit.is_merge:
            chosen.add(commit.sha)
    seen: set[str] = set()
    result: list[str] = []
    for commit in chunk:
        subject = _clip(commit.subject)
        if commit.sha in chosen and subject and subject not in seen:
            seen.add(subject)
            result.append(subject)
    return result


def _area(path: str) -> str:
    parts = PurePosixPath(path).parts
    return f"{parts[0]}/" if len(parts) > 1 else "the project root"


def is_bot(name: str, email: str = "") -> bool:
    """Return ``True`` for automation accounts such as Dependabot or GitHub Actions."""
    return bool(_BOT.search(name) or _BOT.search(email.split("@", 1)[0]))


# --------------------------------------------------------------------------- vocabulary


def _vocabulary(commits: Sequence[Commit], limit: int = 10) -> list[str]:
    words: Counter[str] = Counter()
    for commit in commits:
        if commit.is_merge:
            continue
        for word in _WORD.findall(commit.subject.lower()):
            if word not in _STOPWORDS:
                words[word] += 1
    return [word for word, count in words.most_common(limit) if count > 1]


# --------------------------------------------------------------------------- helpers


def _clip(text: str, limit: int = MAX_SUBJECT_LENGTH) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _join(items: Sequence[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" and {items[-1]}"


def format_span(first: datetime, last: datetime) -> str:
    """Return a compact human description of a time span, such as ``2 years, 3 months``."""
    days = max(0, (last - first).days)
    years, days = divmod(days, 365)
    months, days = divmod(days, 30)
    parts = []
    if years:
        parts.append(f"{years} year{'s' * (years != 1)}")
    if months:
        parts.append(f"{months} month{'s' * (months != 1)}")
    if not parts:
        parts.append(f"{days} day{'s' * (days != 1)}")
    return ", ".join(parts)
