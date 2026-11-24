# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- A per-user `.env` file at `~/.config/repodoc/.env` (or `$XDG_CONFIG_HOME/repodoc/.env`) is loaded
  automatically, so the API key works from any directory.

## [0.1.0] - 2026-11-24

### Added

- `repodoc` command line tool for local repositories and remote URLs.
- Deterministic history analysis: overview, contributor roles, story moments and acts.
- Six documentary styles: nature, true crime, epic, sports, noir and trailer.
- OpenAI narrator using the Responses API with configurable model and reasoning effort.
- Offline template narrator that needs no network or API key.
- Terminal, Markdown, JSON and self-contained HTML output.
- `--anonymize`, `--language`, `--since`, `--until`, `--max-commits` and `--dossier` options.

[0.1.0]: https://github.com/001shahab/RepoDocumentary/releases/tag/v0.1.0
