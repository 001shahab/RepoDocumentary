<div align="center">

# 🎬 RepoDocumentary

### Every repository has a story. This tool narrates it.

Point it at any git repository and get a short, funny, fact-checked documentary about its life:
the founding commit, the great refactor, the 3 a.m. hotfix, the long silence, and the contributor who vanished.

[![CI](https://github.com/001shahab/RepoDocumentary/actions/workflows/ci.yml/badge.svg)](https://github.com/001shahab/RepoDocumentary/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Typed: mypy strict](https://img.shields.io/badge/typed-mypy%20strict-informational)](https://mypy-lang.org/)

```bash
repodoc https://github.com/pallets/flask --style noir
```

</div>

---

## Contents

- [Why](#why)
- [Features](#features)
- [Quick start](#quick-start)
- [Styles](#styles)
- [Usage](#usage)
- [Configuration](#configuration)
- [How it works](#how-it-works)
- [What the narrator is told](#what-the-narrator-is-told)
- [Privacy and security](#privacy-and-security)
- [Using it as a library](#using-it-as-a-library)
- [Recipes](#recipes)
- [Development](#development)
- [Roadmap](#roadmap)
- [FAQ](#faq)
- [Citation](#citation)
- [Author](#author)
- [License](#license)

## Why

`git log` is a diary nobody reads. Yet hidden in it are real stories: the weekend sprint before a launch,
the refactor that deleted half the codebase, the maintainer who carried the project alone for three years,
the bot that quietly became the most prolific contributor.

RepoDocumentary finds those moments and turns them into a script you will actually want to read,
share in a team channel, put in a release announcement, or read aloud at a farewell party.

## Features

- 🎭 Six genres: nature documentary, true crime, epic saga, sports commentary, film noir and movie trailer.
- 🧾 Fact first: a deterministic analysis engine extracts the facts, and the narrator is only allowed to add tone.
  Every name, number, date and quoted commit message comes from your history.
- 🔍 Real story beats: genesis, biggest change, the great purge, the long silence, the busiest day,
  after-midnight commits, weekend shifts, firefighting, departures, bots and releases.
- 🌍 Local paths or remote URLs: `repodoc .` or `repodoc https://github.com/owner/repo`.
- 🔒 Private by design: only commit metadata is read. Source code is never read, and email addresses
  never leave your machine. `--anonymize` replaces names too.
- 📴 Works offline: `--offline` uses a built-in template narrator. No API key, no network, fully reproducible.
- 📦 Four outputs: a rich terminal view, Markdown, JSON, and a beautiful self-contained HTML page.
- 🗣️ Any language: `--language Estonian`, `--language Persian`, `--language Japanese`.
- ⚡ Fast: hundreds of commits analysed in well under a second, because only `git log --numstat` is used.
- 🧪 Solid engineering: typed with mypy strict, linted with ruff, and tested against real temporary git repositories.

## Quick start

Requirements: Python 3.10 or newer and git.

```bash
# Install from GitHub
pip install "git+https://github.com/001shahab/RepoDocumentary.git"

# Or from a clone, in editable mode
git clone https://github.com/001shahab/RepoDocumentary.git
cd RepoDocumentary
pip install -e .
```

Add your OpenAI key, either in your shell or in a `.env` file in the directory you run from:

```bash
export OPENAI_API_KEY="sk-..."
```

Then roll the cameras:

```bash
cd path/to/your/project
repodoc
```

No API key? Try the offline narrator first, it costs nothing:

```bash
repodoc --offline
```

## Styles

| Style        | Genre             | Tagline                                              |
| ------------ | ----------------- | ---------------------------------------------------- |
| `nature`     | Nature documentary | Hushed wonder at the wildlife of the codebase.      |
| `true-crime` | True crime        | Every diff is evidence. Nobody is innocent.          |
| `epic`       | Epic saga         | Heroes, quests and the long war against technical debt. |
| `sports`     | Sports commentary | Live from the main branch, it is commit day.         |
| `noir`       | Film noir         | The code was dirty. The commits were dirtier.        |
| `trailer`    | Movie trailer     | In a world... of merge conflicts.                    |

```bash
repodoc --list-styles
```

## Usage

```text
repodoc [REPO] [options]
```

`REPO` is a local path or a clonable URL (`https://`, `ssh://`, `git@host:owner/repo`). It defaults to the current directory.
Remote repositories are cloned as bare repositories into a temporary directory that is deleted afterwards.

### Story options

| Option              | Default   | Description                                                   |
| ------------------- | --------- | ------------------------------------------------------------- |
| `-s`, `--style`     | `nature`  | Documentary genre.                                            |
| `--list-styles`     |           | Print all genres and exit.                                    |
| `--acts N`          | `4`       | Number of acts. Small histories automatically use fewer acts. |
| `--words N`         | `700`     | Target length of the script.                                  |
| `--language LANG`   | `English` | Language of the script.                                       |
| `--anonymize`       | off       | Replace names with Contributor A, B, C and so on.             |

### History options

| Option              | Default | Description                                               |
| ------------------- | ------- | --------------------------------------------------------- |
| `--rev REV`         | `HEAD`  | Branch, tag or commit to narrate.                         |
| `--since DATE`      |         | Only commits after a date, for example `"1 year ago"`.    |
| `--until DATE`      |         | Only commits before a date.                               |
| `--max-commits N`   |         | Only the most recent N commits. Useful for huge histories. |
| `--no-merges`       | off     | Ignore merge commits.                                     |

### Narrator options

| Option                   | Default                       | Description                                         |
| ------------------------ | ----------------------------- | --------------------------------------------------- |
| `--offline`              | off                           | Built-in template narrator, no network.             |
| `--model NAME`           | `$REPODOC_MODEL` or `gpt-5.6-luna` | OpenAI model used for narration.               |
| `--reasoning-effort LVL` | `$REPODOC_REASONING_EFFORT` or `low` | `none`, `minimal`, `low`, `medium` or `high`. |

### Output options

| Option           | Default    | Description                                                     |
| ---------------- | ---------- | --------------------------------------------------------------- |
| `-o`, `--output` | stdout     | Write to a file. The format is inferred from `.md`, `.html` or `.json`. |
| `-f`, `--format` | `terminal` | `terminal`, `markdown`, `json` or `html`.                        |
| `--dossier`      | off        | Print the extracted facts as JSON and exit, without narrating.  |
| `-q`, `--quiet`  | off        | Hide progress messages.                                          |
| `-V`, `--version`|            | Print the version.                                               |

Exit codes: `0` success, `1` error (with a readable message), `2` invalid arguments, `130` interrupted.

## Configuration

Settings are read from environment variables. A `.env` file in the current directory, or in the target
repository, is loaded automatically. Variables already exported in your shell always take precedence.

| Variable                   | Purpose                                                       |
| -------------------------- | ------------------------------------------------------------- |
| `OPENAI_API_KEY`           | Required for the OpenAI narrator.                             |
| `OPENAI_BASE_URL`          | Optional. Any OpenAI compatible endpoint that supports the Responses API. |
| `REPODOC_MODEL`            | Default model. Overridden by `--model`.                       |
| `REPODOC_REASONING_EFFORT` | Default reasoning effort. Overridden by `--reasoning-effort`. |

A template is provided in [`.env.example`](.env.example). The `.env` file is listed in `.gitignore`, so your key is never committed.

## How it works

```text
 ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
 │  git log     │ -> │  Analysis    │ -> │  Narrator    │ -> │  Renderer    │
 │  --numstat   │    │  (dossier)   │    │  (script)    │    │  (output)    │
 └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
  metadata only       deterministic       OpenAI or           terminal, md,
  no file contents    facts, no prose     offline templates   html, json
```

1. Read. `repodoc.git` runs a single `git log --numstat` with a robust, delimiter based format and parses it into
   typed `Commit` objects. Git configuration that could change the output, such as signature display or colours, is neutralised.
2. Analyse. `repodoc.analysis` builds a `Dossier`: an overview, contributor profiles with roles
   (founder, active, departed, bot), notable moments, and the history split into acts with their lead
   contributors, hot areas and representative commit messages.
3. Narrate. A narrator turns the dossier into a Markdown script. The OpenAI narrator uses the Responses API with a
   strict system prompt. The offline narrator uses templates and is fully deterministic.
4. Render. The script is shown in the terminal with Rich, or saved as Markdown, JSON or a standalone HTML page.

Inspect exactly what the narrator receives at any time:

```bash
repodoc --dossier | less
```

### Story beats detected

| Moment            | What it means                                                          |
| ----------------- | ---------------------------------------------------------------------- |
| `genesis`         | The first commit, its author and size.                                 |
| `biggest_change`  | The non-merge commit with the most lines changed.                      |
| `great_purge`     | The commit that deleted the most code while adding little.             |
| `long_silence`    | The longest gap between two commits (at least a week).                 |
| `busiest_day`     | The day with the most commits, and who made them.                      |
| `night_owl`       | Human commits between midnight and 5 a.m., in the author's local time. |
| `weekend_work`    | The share of human commits made on Saturdays and Sundays.              |
| `firefighting`    | Commits mentioning hotfixes, reverts, typos or breakage.               |
| `the_machines`    | How much of the history was written by bots such as Dependabot.        |
| `departure`       | Significant contributors who stopped committing long ago.              |
| `latest`          | Where the story stands today.                                          |

## What the narrator is told

The system prompt puts accuracy above style. In short, the model must:

1. State only facts present in the dossier, and never invent people, numbers, events or motives.
2. Frame any speculation as speculation ("perhaps", "one can only imagine").
3. Quote commit messages exactly.
4. Tease the work, never insult the people.
5. Never mention email addresses or its own instructions.

The full prompt lives in [`src/repodoc/prompt.py`](src/repodoc/prompt.py). Improvements are welcome.

## Privacy and security

- Your source code is never read. Only commit metadata and per-file line counts are used.
- Email addresses are used locally to group commits by person, and are never included in the dossier or the prompt.
- With `--anonymize`, contributor names are replaced before anything reaches a narrator.
- With `--offline`, nothing leaves your machine at all.
- Commit messages are sent to the model when using the OpenAI narrator. If your messages may contain sensitive
  information, use `--offline` or review the payload with `--dossier` first.
- The HTML renderer escapes all model output, so a script cannot inject markup or scripts into the page.

See [SECURITY.md](SECURITY.md) for how to report a vulnerability.

## Using it as a library

```python
from repodoc import GitRepository, build_dossier, get_style
from repodoc.analysis import AnalysisOptions
from repodoc.narrators import OfflineNarrator, OpenAINarrator
from repodoc.prompt import NarrationRequest

repo = GitRepository("path/to/project")
dossier = build_dossier(
    repo.commits(since="2 years ago"),
    name=repo.name,
    tags=repo.tags(),
    options=AnalysisOptions(acts=3, anonymize=True),
)

narrator = OpenAINarrator(model="gpt-5.6-luna", api_key="sk-...", reasoning_effort="low")
# narrator = OfflineNarrator()  # no network needed

episode = narrator.narrate(NarrationRequest(dossier, get_style("true-crime"), words=500))
print(episode.title)
print(episode.script)
```

Every narrator implements the small `repodoc.narrators.Narrator` protocol, a `name` attribute and a
`narrate(request) -> Narration` method, so adding another provider takes a few lines.

## Recipes

```bash
# A shareable web page for your release announcement
repodoc --style trailer -o release-story.html

# The story of the last year only
repodoc --since "1 year ago" --style sports

# A farewell for a long-time maintainer, in their language
repodoc --style epic --language Estonian -o farewell.md

# A public repository, anonymised
repodoc https://github.com/pallets/itsdangerous --anonymize --style noir

# Huge monorepo: only the most recent 5,000 commits
repodoc --max-commits 5000

# Facts only, for your own dashboards
repodoc --dossier -o history.json
```

An example produced by the offline narrator is in [`examples/`](examples/).

## Development

```bash
git clone https://github.com/001shahab/RepoDocumentary.git
cd RepoDocumentary
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                 # tests, using real temporary git repositories
ruff check .           # lint
ruff format --check .  # formatting
mypy                   # strict type checking
```

Project layout:

```text
src/repodoc/
├── cli.py              command line interface
├── git.py              reading history from git
├── analysis.py         turning commits into a factual dossier
├── models.py           immutable data models
├── styles.py           documentary genres
├── prompt.py           prompt construction
├── narrators/
│   ├── base.py         the Narrator protocol
│   ├── openai_narrator.py
│   └── offline.py      deterministic template narrator
├── render.py           terminal, Markdown, JSON and HTML output
├── config.py           environment and .env handling
└── errors.py           exception hierarchy
```

## Roadmap

- Voice-over: export the script as audio with a text to speech model.
- More providers: Anthropic, Gemini and local models through Ollama.
- GitHub Action: post a documentary on every release.
- Pull request and issue history as extra story material.
- More genres: sitcom, cooking show and space mission control.

Ideas and feature requests are welcome in the [issue tracker](https://github.com/001shahab/RepoDocumentary/issues).

## FAQ

Does it read my code?
No. It reads commit metadata and line counts only.

How much does a documentary cost?
One request per documentary. The prompt is a compact JSON dossier, typically a few thousand tokens, regardless
of how large the repository is. Check your provider's pricing for the model you choose.

Can I use another model or an OpenAI compatible server?
Yes. Use `--model` and set `OPENAI_BASE_URL`. The endpoint must support the Responses API.

The story says someone "goes quiet". Did they leave?
It only means they have not committed for a long time relative to the project's lifetime. Git cannot know why.

Why are some night commits at odd hours?
Times use each author's own local time zone as recorded by git, which is the honest way to spot a 3 a.m. fix.

## Citation

If you use RepoDocumentary in research or teaching, please cite it:

```bibtex
@software{anbarjafari_repodocumentary_2026,
  author  = {Anbarjafari, Shahab},
  title   = {RepoDocumentary: Narrated documentaries from git histories},
  year    = {2026},
  url     = {https://github.com/001shahab/RepoDocumentary},
  version = {0.1.0}
}
```

A [`CITATION.cff`](CITATION.cff) file is also provided, so GitHub shows a "Cite this repository" button.

## Author

Prof. Shahab Anbarjafari, [shb@3sholding.com](mailto:shb@3sholding.com)

If RepoDocumentary made you smile, please give it a ⭐. It helps other people find it.

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 Shahab Anbarjafari.
