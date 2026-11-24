from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repodoc.analysis import build_dossier
from repodoc.errors import ConfigurationError, NarrationError
from repodoc.git import GitRepository
from repodoc.models import Dossier
from repodoc.narrators import Narrator, OfflineNarrator, OpenAINarrator, extract_title
from repodoc.prompt import SYSTEM_PROMPT, NarrationRequest, build_user_prompt
from repodoc.styles import STYLES, get_style


@pytest.fixture
def dossier(story_repo: Path) -> Dossier:
    git = GitRepository(story_repo)
    return build_dossier(git.commits(), name="project", tags=git.tags())


class FakeResponses:
    def __init__(
        self, text: str = "# The Engine Years\n\n*A tale.*\n", error: Exception | None = None
    ) -> None:
        self.text, self.error = text, error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        usage = SimpleNamespace(input_tokens=1200, output_tokens=800)
        return SimpleNamespace(output_text=self.text, usage=usage, model=kwargs["model"])


def _client(responses: FakeResponses) -> SimpleNamespace:
    return SimpleNamespace(responses=responses)


@pytest.mark.parametrize("style", sorted(STYLES))
def test_offline_narrator_every_style(dossier: Dossier, style: str) -> None:
    narration = OfflineNarrator().narrate(NarrationRequest(dossier, get_style(style)))
    assert narration.script.startswith("# project")
    assert "## Act I" in narration.script
    assert "## Epilogue" in narration.script
    assert '"Initial commit"' in narration.script
    assert narration.narrator == "offline"


def test_offline_narrator_is_deterministic(dossier: Dossier) -> None:
    request = NarrationRequest(dossier, get_style("noir"))
    assert OfflineNarrator().narrate(request) == OfflineNarrator().narrate(request)


def test_narrators_satisfy_protocol() -> None:
    fake = OpenAINarrator(model="m", api_key=None, client=_client(FakeResponses()))
    assert isinstance(OfflineNarrator(), Narrator)
    assert isinstance(fake, Narrator)


def test_openai_narrator_sends_reasoning_and_prompt(dossier: Dossier) -> None:
    responses = FakeResponses()
    narrator = OpenAINarrator(
        model="gpt-test", api_key=None, reasoning_effort="low", client=_client(responses)
    )
    narration = narrator.narrate(NarrationRequest(dossier, get_style("epic"), words=300))

    call = responses.calls[0]
    assert call["model"] == "gpt-test"
    assert call["reasoning"] == {"effort": "low"}
    assert call["instructions"] == SYSTEM_PROMPT
    assert "Epic saga" in call["input"]
    assert "about 300 words" in call["input"]
    assert narration.title == "The Engine Years"
    assert narration.input_tokens == 1200
    assert narration.model == "gpt-test"


def test_reasoning_none_is_omitted(dossier: Dossier) -> None:
    responses = FakeResponses()
    OpenAINarrator(
        model="m", api_key=None, reasoning_effort="none", client=_client(responses)
    ).narrate(NarrationRequest(dossier, get_style("nature")))
    assert "reasoning" not in responses.calls[0]


def test_missing_api_key() -> None:
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        OpenAINarrator(model="m", api_key=None)


def test_invalid_reasoning_effort() -> None:
    with pytest.raises(ConfigurationError):
        OpenAINarrator(model="m", api_key="k", reasoning_effort="extreme")


def test_api_errors_become_narration_errors(dossier: Dossier) -> None:
    error = RuntimeError("boom")
    error.status_code = 401  # type: ignore[attr-defined]
    narrator = OpenAINarrator(model="m", api_key=None, client=_client(FakeResponses(error=error)))
    with pytest.raises(NarrationError, match="API key was rejected"):
        narrator.narrate(NarrationRequest(dossier, get_style("nature")))


def test_empty_output_is_an_error(dossier: Dossier) -> None:
    narrator = OpenAINarrator(model="m", api_key=None, client=_client(FakeResponses(text="  ")))
    with pytest.raises(NarrationError, match="empty"):
        narrator.narrate(NarrationRequest(dossier, get_style("nature")))


def test_user_prompt_contains_facts_but_no_emails(dossier: Dossier) -> None:
    prompt = build_user_prompt(NarrationRequest(dossier, get_style("noir"), language="Estonian"))
    assert "Ada Lovelace" in prompt
    assert "Remove legacy engine" in prompt
    assert "Estonian" in prompt
    assert "@example.com" not in prompt


def test_extract_title() -> None:
    assert extract_title("intro\n# Big Title\n## Act I", "x") == "Big Title"
    assert extract_title("no heading", "fallback") == "fallback"


def test_unknown_style() -> None:
    with pytest.raises(KeyError, match="Available styles"):
        get_style("opera")
