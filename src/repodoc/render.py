"""Output formats: terminal, Markdown, JSON and a self-contained HTML page."""

from __future__ import annotations

import html
import json
import re
from enum import Enum

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from repodoc import __version__
from repodoc.analysis import format_span
from repodoc.models import Dossier, Narration

PROJECT_URL = "https://github.com/001shahab/RepoDocumentary"


class OutputFormat(str, Enum):
    TERMINAL = "terminal"
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"

    @classmethod
    def from_path(cls, path: str) -> OutputFormat:
        suffix = path.lower().rsplit(".", 1)[-1] if "." in path else ""
        return {
            "md": cls.MARKDOWN,
            "markdown": cls.MARKDOWN,
            "json": cls.JSON,
            "html": cls.HTML,
            "htm": cls.HTML,
        }.get(suffix, cls.MARKDOWN)


def credits_line(narration: Narration) -> str:
    voice = f"{narration.narrator} ({narration.model})" if narration.model else narration.narrator
    return f"Narrated by {voice} in the {narration.style} style with RepoDocumentary {__version__}"


def to_markdown(narration: Narration, dossier: Dossier) -> str:
    overview = dossier.overview
    span = format_span(overview.first_commit_at, overview.last_commit_at)
    footer = (
        "\n---\n\n"
        f"**{overview.name}** in numbers: {overview.total_commits} commits, "
        f"{overview.contributors} contributors, {span}, "
        f"+{overview.insertions} / -{overview.deletions} lines.\n\n"
        f"<sub>{credits_line(narration)}. [Make your own]({PROJECT_URL}).</sub>\n"
    )
    return narration.script.rstrip() + "\n" + footer


def to_json(narration: Narration, dossier: Dossier) -> str:
    document = {"narration": narration.to_dict(), "dossier": dossier.to_dict()}
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def to_html(narration: Narration, dossier: Dossier) -> str:
    overview = dossier.overview
    span = format_span(overview.first_commit_at, overview.last_commit_at)
    body = markdown_to_html(narration.script)
    stats = (
        f"{overview.total_commits} commits &middot; {overview.contributors} contributors "
        f"&middot; {html.escape(span)} &middot; +{overview.insertions} / -{overview.deletions}"
    )
    return _HTML_TEMPLATE.format(
        title=html.escape(narration.title),
        body=body,
        stats=stats,
        credits=html.escape(credits_line(narration)),
        url=PROJECT_URL,
    )


def render(narration: Narration, dossier: Dossier, fmt: OutputFormat) -> str:
    """Return the narration in a file format. ``TERMINAL`` falls back to Markdown."""
    if fmt is OutputFormat.JSON:
        return to_json(narration, dossier)
    if fmt is OutputFormat.HTML:
        return to_html(narration, dossier)
    return to_markdown(narration, dossier)


def print_to_terminal(narration: Narration, dossier: Dossier, console: Console) -> None:
    overview = dossier.overview
    stats = Table.grid(padding=(0, 2))
    stats.add_column(style="bold cyan")
    stats.add_column()
    stats.add_row("Commits", f"{overview.total_commits:,}")
    stats.add_row("Contributors", f"{overview.contributors:,}")
    stats.add_row("Span", format_span(overview.first_commit_at, overview.last_commit_at))
    stats.add_row("Lines", f"+{overview.insertions:,} / -{overview.deletions:,}")
    if overview.languages:
        stats.add_row("Languages", ", ".join(overview.languages[:3]))

    console.print()
    console.print(
        Panel(
            Group(Markdown(narration.script), Rule(style="dim"), stats),
            title=f"[bold]RepoDocumentary[/] [dim]{overview.name}[/]",
            subtitle=f"[dim]{credits_line(narration)}[/]",
            border_style="magenta",
            padding=(1, 2),
        )
    )


_INLINE_EM = re.compile(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])")
_INLINE_STRONG = re.compile(r"\*\*(?!\s)(.+?)(?<!\s)\*\*")


def markdown_to_html(markdown: str) -> str:
    """Convert the small Markdown subset narrators produce into safe HTML.

    Supported: ``#`` to ``###`` headings, paragraphs, ``*emphasis*``, ``**strong**`` and
    ``---`` rules. Everything is HTML-escaped first, so model output cannot inject markup.
    """
    blocks: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            blocks.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading:
            flush()
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
        elif line in {"---", "***", "___"}:
            flush()
            blocks.append("<hr>")
        else:
            paragraph.append(line)
    flush()
    return "\n".join(blocks)


def _inline(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = _INLINE_STRONG.sub(r"<strong>\1</strong>", escaped)
    return _INLINE_EM.sub(r"<em>\1</em>", escaped)


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="RepoDocumentary">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; --ink: #1d1b22; --paper: #f7f4ee; --accent: #b4235a; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --ink: #ece8e1; --paper: #141218; --accent: #ff6b9d; }}
  }}
  body {{ margin: 0; background: var(--paper); color: var(--ink);
         font: 19px/1.7 Georgia, "Iowan Old Style", serif; }}
  main {{ max-width: 42rem; margin: 0 auto; padding: 4rem 1.5rem 6rem; }}
  h1 {{ font-size: 2.4rem; line-height: 1.15; margin: 0 0 1rem; letter-spacing: -0.02em; }}
  h2 {{ font: 600 0.85rem/1.4 ui-sans-serif, system-ui, sans-serif; text-transform: uppercase;
        letter-spacing: 0.14em; color: var(--accent); margin: 3rem 0 0.75rem; }}
  em {{ opacity: 0.85; }}
  hr {{ border: 0; border-top: 1px solid currentColor; opacity: 0.2; margin: 3rem 0; }}
  footer {{ font: 0.8rem/1.6 ui-sans-serif, system-ui, sans-serif; opacity: 0.7; }}
  a {{ color: var(--accent); }}
</style>
</head>
<body>
<main>
{body}
<hr>
<footer>
  <p>{stats}</p>
  <p>{credits}. <a href="{url}">Make your own documentary</a>.</p>
</footer>
</main>
</body>
</html>
"""
