"""Narrative styles. Each style is a short directing brief for the narrator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Style:
    """A documentary genre."""

    key: str
    label: str
    tagline: str
    direction: str
    opening: str
    closing: str


STYLES: dict[str, Style] = {
    style.key: style
    for style in (
        Style(
            key="nature",
            label="Nature documentary",
            tagline="Hushed wonder at the wildlife of the codebase.",
            direction=(
                "Narrate like a calm, awe-struck wildlife documentary. Treat contributors as "
                "remarkable creatures, commits as behaviour observed in the wild, refactors as "
                "migrations and releases as the changing of seasons. Gentle, wry humour."
            ),
            opening="Here, in the quiet of an empty directory, life is about to begin.",
            closing="And so the repository endures, as it always has, one commit at a time.",
        ),
        Style(
            key="true-crime",
            label="True crime",
            tagline="Every diff is evidence. Nobody is innocent.",
            direction=(
                "Narrate like a gripping true-crime series. Present commits as evidence, "
                "timestamps as alibis and suspicious late-night changes as leads. Build tension, "
                "use cliffhangers between acts, and keep it playful rather than accusatory."
            ),
            opening="It started, as these things often do, with a single, innocent commit.",
            closing="The case remains open. The repository is still accepting commits.",
        ),
        Style(
            key="epic",
            label="Epic saga",
            tagline="Heroes, quests and the long war against technical debt.",
            direction=(
                "Narrate like a grand fantasy saga. Contributors are heroes on a quest, the "
                "biggest changes are battles, deleted code is a fallen kingdom and releases are "
                "coronations. Sweeping, mythic language, but keep sentences readable."
            ),
            opening="In the age before the first commit, there was only the void.",
            closing="The saga is not over. Somewhere, a branch is being drawn.",
        ),
        Style(
            key="sports",
            label="Sports commentary",
            tagline="Live from the main branch, it is commit day.",
            direction=(
                "Narrate like energetic live sports commentary with two-commentator energy "
                "in a single voice. Commits are plays, busy days are big matches, streaks are "
                "records and releases are trophies. Fast, punchy, full of statistics."
            ),
            opening="Welcome, everyone, to what promises to be an extraordinary history!",
            closing="What a season. We will be right back after this short merge.",
        ),
        Style(
            key="noir",
            label="Film noir",
            tagline="The code was dirty. The commits were dirtier.",
            direction=(
                "Narrate like a hard-boiled 1940s film noir detective in the first person. "
                "Rain-soaked metaphors, terse sentences, cynical observations about deadlines, "
                "and a reluctant fondness for the people who wrote the code."
            ),
            opening="The repository was quiet. Too quiet. Then the first commit walked in.",
            closing="I closed the terminal. Somewhere out there, the build was still running.",
        ),
        Style(
            key="trailer",
            label="Movie trailer",
            tagline="In a world... of merge conflicts.",
            direction=(
                "Write it as a dramatic blockbuster movie trailer voice-over. Short, booming "
                "lines, 'In a world...' energy, rising stakes, and a title card at the end. "
                "Keep it shorter than the other styles."
            ),
            opening="In a world where every line of code matters...",
            closing="Coming soon to a terminal near you.",
        ),
    )
}

DEFAULT_STYLE = "nature"


def get_style(key: str) -> Style:
    """Return the style registered under *key* (case insensitive)."""
    try:
        return STYLES[key.strip().lower()]
    except KeyError:
        available = ", ".join(sorted(STYLES))
        raise KeyError(f"Unknown style {key!r}. Available styles: {available}") from None
