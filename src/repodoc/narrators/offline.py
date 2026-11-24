"""A deterministic narrator that needs no network and no API key.

It is less witty than a language model, but it is instant, free, reproducible and safe
for CI pipelines. It also serves as a reference for what a narrator must produce.
"""

from __future__ import annotations

from collections.abc import Sequence

from repodoc.analysis import format_span
from repodoc.models import Act, Dossier, Moment, Narration
from repodoc.prompt import NarrationRequest, roman

_ACT_TITLES: dict[str, Sequence[str]] = {
    "nature": ("First Light", "The Growing Season", "Migration", "The Long Summer", "Dusk"),
    "true-crime": ("The Scene", "The Pattern", "The Suspects", "The Break", "Closing In"),
    "epic": ("The Calling", "The Fellowship", "The Trials", "The Siege", "The Return"),
    "sports": ("Kick-off", "First Half", "Half-time Reshuffle", "Second Half", "Extra Time"),
    "noir": ("The Client", "The Lead", "The Double-Cross", "The Long Night", "The Last Drink"),
    "trailer": ("The Spark", "The Rise", "The Storm", "The Stand", "The Legend"),
}


class OfflineNarrator:
    """Builds a script from templates using only the dossier."""

    name = "offline"

    def narrate(self, request: NarrationRequest) -> Narration:
        dossier, style = request.dossier, request.style
        overview = dossier.overview
        title = f"{overview.name}: A {style.label}"
        moments = {moment.kind: moment for moment in dossier.moments}

        lines = [f"# {title}", "", f"*{style.tagline}*", "", style.opening, ""]
        titles = _ACT_TITLES.get(style.key, _ACT_TITLES["nature"])
        for index, act in enumerate(dossier.acts):
            heading = titles[min(index, len(titles) - 1)]
            lines.append(f"## Act {roman(act.number)}: {heading}")
            lines.append("")
            lines.extend(_act_paragraphs(act, dossier, moments, first=index == 0))
            lines.append("")

        lines.append("## Epilogue")
        lines.append("")
        lines.append(_epilogue(dossier))
        lines.append("")
        lines.append(style.closing)
        script = "\n".join(lines).strip() + "\n"
        return Narration(title=title, script=script, style=style.key, narrator=self.name)


def _act_paragraphs(
    act: Act, dossier: Dossier, moments: dict[str, Moment], *, first: bool
) -> list[str]:
    start, end = act.start.date().isoformat(), act.end.date().isoformat()
    when = start if start == end else f"{start} to {end}"
    cast = _join(list(act.lead_contributors)) or "an unknown hand"
    areas = _join(list(act.hot_paths)) or "the root of the project"
    paragraphs: list[str] = []

    if first and "genesis" in moments:
        paragraphs.append(moments["genesis"].detail)
        paragraphs.append("")

    paragraphs.append(
        f"From {when}, {act.commits} commit{'s' * (act.commits != 1)} arrived, led by {cast}. "
        f"Most of the action happened in {areas}, with {act.insertions} lines written and "
        f"{act.deletions} taken away."
    )
    if act.highlights:
        quoted = ", ".join(f'"{subject}"' for subject in act.highlights[:4])
        paragraphs.append("")
        paragraphs.append(f"The record from this chapter reads: {quoted}.")

    for moment in dossier.moments:
        if moment.kind in {"genesis", "latest"} or moment.at is None:
            continue
        if act.start <= moment.at <= act.end:
            paragraphs.append("")
            paragraphs.append(f"{moment.title}. {moment.detail}")
    return paragraphs


def _epilogue(dossier: Dossier) -> str:
    overview = dossier.overview
    span = format_span(overview.first_commit_at, overview.last_commit_at)
    people = f"{overview.contributors} contributor{'s' * (overview.contributors != 1)}"
    sentence = (
        f"Over {span}, {people} made {overview.total_commits} commits, writing "
        f"{overview.insertions} lines and deleting {overview.deletions}."
    )
    if overview.languages:
        sentence += f" The project speaks mostly {_join(list(overview.languages[:3]))}."
    if dossier.vocabulary:
        words = ", ".join(f'"{word}"' for word in dossier.vocabulary[:5])
        sentence += f" Its favourite words: {words}."
    return sentence


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" and {items[-1]}"
