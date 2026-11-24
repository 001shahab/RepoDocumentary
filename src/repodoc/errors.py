"""Exception hierarchy.

Every error raised on purpose by RepoDocumentary derives from :class:`RepoDocError`,
so callers embedding the library can catch a single type.
"""

from __future__ import annotations


class RepoDocError(Exception):
    """Base class for all RepoDocumentary errors."""


class GitError(RepoDocError):
    """A git command failed or git is not available."""


class NotARepositoryError(GitError):
    """The given path is not inside a git repository."""


class EmptyRepositoryError(GitError):
    """The repository (or the selected range) has no commits."""


class ConfigurationError(RepoDocError):
    """Required configuration, such as an API key, is missing or invalid."""


class NarrationError(RepoDocError):
    """The narrator could not produce a script."""
