"""Command line interface: ``repodoc [REPO] [options]``."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager, nullcontext
from pathlib import Path

from rich.console import Console
from rich.table import Table

from repodoc import __version__
from repodoc.analysis import AnalysisOptions, build_dossier
from repodoc.config import Settings, load_dotenv_files
from repodoc.errors import RepoDocError
from repodoc.git import GitRepository, clone_remote, is_remote_url
from repodoc.models import Dossier
from repodoc.narrators import REASONING_EFFORTS, Narrator, OfflineNarrator, OpenAINarrator
from repodoc.prompt import NarrationRequest
from repodoc.render import OutputFormat, print_to_terminal, render
from repodoc.styles import DEFAULT_STYLE, STYLES, get_style

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INTERRUPTED = 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repodoc",
        description=(
            "Turn a git history into a narrated documentary. Reads commit metadata only; "
            "your source code is never sent anywhere."
        ),
        epilog=(
            "examples:\n"
            "  repodoc                              narrate the repository you are in\n"
            "  repodoc ~/code/app --style noir      pick a genre\n"
            "  repodoc https://github.com/psf/requests -o requests.html\n"
            "  repodoc --offline                    no API key needed\n"
            "  repodoc --dossier                    show the facts the narrator receives"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="path to a local repository or a clonable URL (default: current directory)",
    )

    story = parser.add_argument_group("story")
    story.add_argument(
        "-s",
        "--style",
        default=DEFAULT_STYLE,
        choices=sorted(STYLES),
        metavar="STYLE",
        help=f"documentary genre (default: {DEFAULT_STYLE}); see --list-styles",
    )
    story.add_argument("--list-styles", action="store_true", help="list genres and exit")
    story.add_argument("--acts", type=_positive_int, default=4, help="number of acts (default: 4)")
    story.add_argument(
        "--words", type=_positive_int, default=700, help="target length in words (default: 700)"
    )
    story.add_argument(
        "--language", default="English", help="language of the script (default: English)"
    )
    story.add_argument(
        "--anonymize",
        action="store_true",
        help="replace contributor names with Contributor A, B, C...",
    )

    history = parser.add_argument_group("history")
    history.add_argument("--rev", default="HEAD", help="branch, tag or commit (default: HEAD)")
    history.add_argument("--since", help='only commits after this date, e.g. "2 years ago"')
    history.add_argument("--until", help="only commits before this date")
    history.add_argument(
        "--max-commits", type=_positive_int, help="analyse only the most recent N commits"
    )
    history.add_argument("--no-merges", action="store_true", help="ignore merge commits")

    narrator = parser.add_argument_group("narrator")
    narrator.add_argument(
        "--offline",
        action="store_true",
        help="use the built-in template narrator (no network, no API key)",
    )
    narrator.add_argument("--model", help="OpenAI model (default: $REPODOC_MODEL or built-in)")
    narrator.add_argument(
        "--reasoning-effort",
        choices=REASONING_EFFORTS,
        help="reasoning effort for reasoning models (default: $REPODOC_REASONING_EFFORT or low)",
    )

    output = parser.add_argument_group("output")
    output.add_argument("-o", "--output", help="write to a file (.md, .html or .json)")
    output.add_argument(
        "-f",
        "--format",
        choices=[fmt.value for fmt in OutputFormat],
        help="output format (default: terminal, or inferred from --output)",
    )
    output.add_argument(
        "--dossier",
        action="store_true",
        help="print the extracted facts as JSON and exit without narrating",
    )
    output.add_argument("-q", "--quiet", action="store_true", help="hide progress messages")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    console = Console()
    errors = Console(stderr=True)

    if args.list_styles:
        _print_styles(console)
        return EXIT_OK

    try:
        return _run(args, console, errors)
    except RepoDocError as exc:
        errors.print(f"[bold red]error:[/] {exc}")
        return EXIT_ERROR
    except KeyboardInterrupt:
        errors.print("[yellow]Interrupted.[/]")
        return EXIT_INTERRUPTED


def _run(args: argparse.Namespace, console: Console, errors: Console) -> int:
    local = None if is_remote_url(args.repo) else Path(args.repo).expanduser()
    load_dotenv_files(*([local] if local else []))
    settings = Settings.from_env()

    with _status(errors, "Reading history...", quiet=args.quiet), _open(args.repo) as repo:
        commits = repo.commits(
            args.rev,
            since=args.since,
            until=args.until,
            max_commits=args.max_commits,
            include_merges=not args.no_merges,
        )
        dossier = build_dossier(
            commits,
            name=repo.name,
            tags=repo.tags(),
            options=AnalysisOptions(acts=args.acts, anonymize=args.anonymize),
        )

    if args.dossier:
        payload = json.dumps(dossier.to_dict(), ensure_ascii=False, indent=2) + "\n"
        _emit(payload, args.output, console, errors, quiet=args.quiet)
        return EXIT_OK

    narrator = _narrator(args, settings)
    request = NarrationRequest(
        dossier=dossier, style=get_style(args.style), words=args.words, language=args.language
    )
    label = "Writing the script..." if args.offline else "The narrator is writing..."
    with _status(errors, label, quiet=args.quiet):
        narration = narrator.narrate(request)

    fmt = _resolve_format(args.format, args.output)
    if fmt is OutputFormat.TERMINAL:
        print_to_terminal(narration, dossier, console)
    else:
        _emit(render(narration, dossier, fmt), args.output, console, errors, quiet=args.quiet)
    return EXIT_OK


@contextmanager
def _open(target: str) -> Iterator[GitRepository]:
    if is_remote_url(target):
        name = target.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1].removesuffix(".git")
        with clone_remote(target) as path:
            yield GitRepository(path, display_name=name or None)
        return
    yield GitRepository(target)


def _narrator(args: argparse.Namespace, settings: Settings) -> Narrator:
    if args.offline:
        return OfflineNarrator()
    return OpenAINarrator(
        model=args.model or settings.model,
        api_key=settings.api_key,
        reasoning_effort=args.reasoning_effort or settings.reasoning_effort,
        base_url=settings.base_url,
    )


def _resolve_format(requested: str | None, output: str | None) -> OutputFormat:
    if requested:
        fmt = OutputFormat(requested)
        if fmt is OutputFormat.TERMINAL and output:
            return OutputFormat.from_path(output)
        return fmt
    return OutputFormat.from_path(output) if output else OutputFormat.TERMINAL


def _emit(text: str, output: str | None, console: Console, errors: Console, *, quiet: bool) -> None:
    if output:
        path = Path(output).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if not quiet:
            errors.print(f"[green]Saved[/] {path}")
    else:
        sys.stdout.write(text)
        sys.stdout.flush()


def _status(console: Console, message: str, *, quiet: bool) -> AbstractContextManager[object]:
    if quiet or not console.is_terminal:
        return nullcontext()
    return console.status(message, spinner="dots")


def _print_styles(console: Console) -> None:
    table = Table(title="Documentary styles", show_lines=False, header_style="bold magenta")
    table.add_column("Style", style="bold")
    table.add_column("Genre")
    table.add_column("Tagline", style="dim")
    for key in sorted(STYLES):
        style = STYLES[key]
        table.add_row(key, style.label, style.tagline)
    console.print(table)


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from None
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def dossier_for(path: str, *, acts: int = 4, anonymize: bool = False) -> Dossier:
    """Convenience helper for scripting: build a dossier for a local repository."""
    repo = GitRepository(path)
    return build_dossier(
        repo.commits(),
        name=repo.name,
        tags=repo.tags(),
        options=AnalysisOptions(acts=acts, anonymize=anonymize),
    )
