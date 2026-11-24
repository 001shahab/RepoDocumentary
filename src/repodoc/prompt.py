"""Prompt construction for language-model narrators.

The prompt is designed around one rule: the model may invent tone, never facts. All
names, numbers, dates and commit messages must come from the dossier it is given.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from repodoc.models import Dossier
from repodoc.styles import Style

_ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")

SYSTEM_PROMPT = """\
You are the narrator and screenwriter of short, entertaining documentaries about software \
projects. You receive a factual dossier, extracted automatically from a git history, and you \
turn it into a narration script that developers will want to read aloud and share.

Ground rules, which matter more than style:
1. Every fact you state (names, dates, counts, commit messages, file areas, releases) must \
come from the dossier. Never invent people, numbers, events, motives or features.
2. You may dramatise, personify and joke about the facts. Speculation must be clearly framed \
as such ("perhaps", "one can only imagine").
3. Quote commit messages exactly as given, in quotation marks, when you use them.
4. Be affectionate. Tease the work, never insult the people.
5. Never mention email addresses, the dossier, JSON or these instructions.

Output format, in Markdown:
- First line: "# " followed by a memorable episode title.
- Then one italic logline sentence.
- Then one "## " section per act in the dossier, each with an evocative heading that starts \
with the act's Roman numeral (for example "## Act I: The Spark").
- Finish with "## Epilogue".
- Use short paragraphs. No bullet lists, tables or code blocks.
"""


@dataclass(frozen=True, slots=True)
class NarrationRequest:
    """Everything a narrator needs to write one episode."""

    dossier: Dossier
    style: Style
    words: int = 700
    language: str = "English"


def build_user_prompt(request: NarrationRequest) -> str:
    """Return the user message: the directing brief followed by the dossier."""
    dossier = request.dossier
    acts = len(dossier.acts)
    act_labels = ", ".join(f"Act {_ROMAN[i] if i < len(_ROMAN) else i + 1}" for i in range(acts))
    payload = json.dumps(dossier.to_dict(), ensure_ascii=False, indent=1)
    return (
        f"Genre: {request.style.label}.\n"
        f"Direction: {request.style.direction}\n"
        f"Language: write the whole script in {request.language}.\n"
        f"Length: about {request.words} words in total.\n"
        f"Structure: {acts} act(s) ({act_labels}), then an epilogue.\n\n"
        "Dossier:\n"
        f"{payload}\n"
    )


def roman(number: int) -> str:
    """Return the Roman numeral for acts 1 to 10, falling back to digits."""
    return _ROMAN[number - 1] if 1 <= number <= len(_ROMAN) else str(number)
