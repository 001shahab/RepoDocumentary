"""RepoDocumentary: turn any git history into a narrated documentary.

The package is organised as a small pipeline:

1. :mod:`repodoc.git` reads the raw commit history from a repository.
2. :mod:`repodoc.analysis` condenses it into a factual :class:`~repodoc.models.Dossier`.
3. A narrator from :mod:`repodoc.narrators` turns the dossier into a script.
4. :mod:`repodoc.render` formats the script for the terminal, Markdown or JSON.
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Shahab Anbarjafari"
__email__ = "shb@3sholding.com"

from repodoc.analysis import build_dossier
from repodoc.git import GitRepository
from repodoc.models import Dossier, Narration
from repodoc.styles import STYLES, Style, get_style

__all__ = [
    "STYLES",
    "Dossier",
    "GitRepository",
    "Narration",
    "Style",
    "__version__",
    "build_dossier",
    "get_style",
]
