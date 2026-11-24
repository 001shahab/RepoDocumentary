# Contributing

Thank you for your interest in RepoDocumentary. Bug reports, ideas for new
genres and story beats, and feedback on the narration are all very welcome.

## Reporting issues

Open an issue at https://github.com/001shahab/RepoDocumentary/issues and include:

- what you ran (the full `repodoc` command),
- what you expected and what happened,
- your Python and git versions,
- if relevant, the output of `repodoc --dossier --anonymize`.

## Development setup

```bash
git clone https://github.com/001shahab/RepoDocumentary.git
cd RepoDocumentary
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Before opening a pull request, make sure all checks pass:

```bash
ruff check .
ruff format --check .
mypy
pytest
```

## Guidelines

- Keep facts and storytelling separate. New story beats belong in `analysis.py`
  and must be covered by tests; narrators only add tone.
- Never send source code or email addresses to a narrator.
- Add or update tests for every behaviour change.
- Keep the public API typed and documented.

## Adding a genre

Add a `Style` to `src/repodoc/styles.py` and act titles to
`src/repodoc/narrators/offline.py`. The test suite runs every style automatically.
