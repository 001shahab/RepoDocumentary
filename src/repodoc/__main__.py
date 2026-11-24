"""Allow ``python -m repodoc``."""

from __future__ import annotations

from repodoc.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
