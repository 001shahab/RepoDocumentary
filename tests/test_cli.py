from __future__ import annotations

import json
from pathlib import Path

import pytest

from repodoc import __version__
from repodoc.cli import main
from repodoc.config import DEFAULT_MODEL, Settings, load_dotenv_files
from repodoc.render import OutputFormat, markdown_to_html


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_list_styles(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--list-styles"]) == 0
    output = capsys.readouterr().out
    assert "true-crime" in output
    assert "noir" in output


def test_dossier_to_stdout(story_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(story_repo), "--dossier", "-q"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["overview"]["total_commits"] == 8


def test_offline_markdown_file(story_repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "out" / "story.md"
    assert main([str(story_repo), "--offline", "-s", "noir", "-o", str(target), "-q"]) == 0
    text = target.read_text(encoding="utf-8")
    assert text.startswith("# project")
    assert "Make your own" in text


def test_offline_html_file(story_repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "story.html"
    assert main([str(story_repo), "--offline", "-o", str(target), "-q"]) == 0
    page = target.read_text(encoding="utf-8")
    assert page.startswith("<!DOCTYPE html>")
    assert "<h2>Act I" in page


def test_offline_json_stdout(story_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(story_repo), "--offline", "-f", "json", "-q"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["narration"]["narrator"] == "offline"
    assert data["dossier"]["overview"]["contributors"] == 2


def test_offline_terminal(story_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(story_repo), "--offline", "--anonymize"]) == 0
    output = capsys.readouterr().out
    assert "Contributor A" in output
    assert "Ada" not in output


def test_missing_key_is_a_friendly_error(
    story_repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(story_repo)
    assert main(["-q"]) == 1
    assert "OPENAI_API_KEY" in capsys.readouterr().err


def test_not_a_repo(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path), "--offline"]) == 1
    assert "Not a git repository" in capsys.readouterr().err


def test_invalid_acts(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--acts", "0"])
    assert "positive integer" in capsys.readouterr().err


def test_settings_from_env() -> None:
    settings = Settings.from_env({"OPENAI_API_KEY": "k", "REPODOC_MODEL": "custom"})
    assert settings.api_key == "k"
    assert settings.model == "custom"
    assert settings.reasoning_effort == "low"
    assert Settings.from_env({}).model == DEFAULT_MODEL


def test_user_config_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_home = tmp_path / "config"
    (config_home / "repodoc").mkdir(parents=True)
    (config_home / "repodoc" / ".env").write_text("OPENAI_API_KEY=from-user-config\n")
    workdir = tmp_path / "elsewhere"
    workdir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.chdir(workdir)
    load_dotenv_files()
    assert Settings.from_env().api_key == "from-user-config"


def test_local_dotenv_beats_user_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_home = tmp_path / "config"
    (config_home / "repodoc").mkdir(parents=True)
    (config_home / "repodoc" / ".env").write_text("OPENAI_API_KEY=from-user-config\n")
    (tmp_path / ".env").write_text("OPENAI_API_KEY=from-cwd\n")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.chdir(tmp_path)
    load_dotenv_files()
    assert Settings.from_env().api_key == "from-cwd"


@pytest.mark.parametrize(
    ("path", "expected"),
    [("a.md", OutputFormat.MARKDOWN), ("a.HTML", OutputFormat.HTML), ("a.json", OutputFormat.JSON)],
)
def test_format_from_path(path: str, expected: OutputFormat) -> None:
    assert OutputFormat.from_path(path) is expected


def test_markdown_to_html_escapes_markup() -> None:
    page = markdown_to_html("# Title <script>\n\n*soft* and **loud**\n\n---\n")
    assert "<script>" not in page
    assert "&lt;script&gt;" in page
    assert "<em>soft</em>" in page
    assert "<strong>loud</strong>" in page
    assert "<hr>" in page
