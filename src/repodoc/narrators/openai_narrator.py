"""Narrator backed by the OpenAI Responses API.

Any OpenAI-compatible endpoint that implements the Responses API can be used by setting
``OPENAI_BASE_URL``.
"""

from __future__ import annotations

from typing import Any

from openai import OpenAI

from repodoc.errors import ConfigurationError, NarrationError
from repodoc.models import Narration
from repodoc.narrators.base import extract_title
from repodoc.prompt import SYSTEM_PROMPT, NarrationRequest, build_user_prompt

REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high")


class OpenAINarrator:
    """Writes scripts with an OpenAI model."""

    name = "openai"

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None,
        reasoning_effort: str | None = "low",
        base_url: str | None = None,
        timeout: float = 180.0,
        client: Any | None = None,
    ) -> None:
        if reasoning_effort is not None and reasoning_effort not in REASONING_EFFORTS:
            choices = ", ".join(REASONING_EFFORTS)
            raise ConfigurationError(f"reasoning effort must be one of: {choices}")
        self.model = model
        self.reasoning_effort = reasoning_effort
        if client is not None:
            self._client = client
            return
        if not api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is not set. Add it to your environment, a .env file in this "
                "directory or ~/.config/repodoc/.env, "
                "or run with --offline for the built-in narrator."
            )
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def narrate(self, request: NarrationRequest) -> Narration:
        options: dict[str, Any] = {
            "model": self.model,
            "instructions": SYSTEM_PROMPT,
            "input": build_user_prompt(request),
        }
        if self.reasoning_effort and self.reasoning_effort != "none":
            options["reasoning"] = {"effort": self.reasoning_effort}

        try:
            response = self._client.responses.create(**options)
        except Exception as exc:
            raise NarrationError(_describe(exc)) from exc

        script = (getattr(response, "output_text", "") or "").strip()
        if not script:
            raise NarrationError("The model returned an empty script. Please try again.")

        usage = getattr(response, "usage", None)
        return Narration(
            title=extract_title(script, fallback=request.dossier.overview.name),
            script=script,
            style=request.style.key,
            narrator=self.name,
            model=getattr(response, "model", None) or self.model,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
        )


def _describe(exc: Exception) -> str:
    """Turn SDK exceptions into one helpful sentence without leaking secrets."""
    status = getattr(exc, "status_code", None)
    kind = type(exc).__name__
    hints = {
        401: "The API key was rejected. Check OPENAI_API_KEY.",
        403: "This API key is not allowed to use the selected model.",
        404: "The model was not found. Check --model or REPODOC_MODEL.",
        429: "Rate limit or quota exceeded. Wait a moment or check your billing.",
    }
    if isinstance(status, int) and status in hints:
        return f"{hints[status]} ({kind}, HTTP {status})"
    message = str(exc).strip().splitlines()[0] if str(exc).strip() else kind
    return f"The language model request failed: {message}"
