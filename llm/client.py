"""Pluggable LLM clients (Groq MVP + mock for tests)."""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from app.config import (
    LLM_API_KEY,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
)
from llm.prompts import ChatMessage

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    """Raised when the LLM provider call fails."""


class LLMClient(ABC):
    """Abstract chat completion client."""

    @abstractmethod
    def complete(self, messages: list[ChatMessage]) -> str:
        """Send messages and return the assistant text content."""


class GroqClient(LLMClient):
    """Groq Chat Completions API implementation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else LLM_API_KEY
        self.model = model or LLM_MODEL
        self.temperature = temperature if temperature is not None else LLM_TEMPERATURE
        self.max_tokens = max_tokens or LLM_MAX_TOKENS

        if not self.api_key:
            raise LLMClientError(
                "LLM_API_KEY is not set. Add your Groq API key to .env "
                "(see https://console.groq.com/)."
            )

        try:
            from groq import Groq
        except ImportError as exc:
            raise LLMClientError(
                "Install the Groq SDK: pip install groq"
            ) from exc

        self._client = Groq(api_key=self.api_key)

    def complete(self, messages: list[ChatMessage]) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except Exception as exc:
            raise LLMClientError(f"Groq API request failed: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMClientError("Groq returned empty content.")
        return content.strip()


class MockLLMClient(LLMClient):
    """
    Deterministic client for tests.

    Returns valid JSON ranking candidates by rating (highest first).
    Parses candidate ids from the user message JSON payload.
    """

    def __init__(self, *, malformed: bool = False, empty: bool = False) -> None:
        self.malformed = malformed
        self.empty = empty
        self.call_count = 0

    def complete(self, messages: list[ChatMessage]) -> str:
        self.call_count += 1

        if self.malformed and self.call_count == 1:
            return "not valid json {{{"

        if self.empty:
            return json.dumps({"summary": "No picks.", "recommendations": []})

        candidates = _extract_candidates_from_messages(messages)
        if not candidates:
            return json.dumps({"summary": "Test summary.", "recommendations": []})

        sorted_candidates = sorted(
            candidates,
            key=lambda c: float(c.get("rating", 0)),
            reverse=True,
        )

        recommendations = []
        for rank, item in enumerate(sorted_candidates[:3], start=1):
            rid = item["id"]
            cuisines = item.get("cuisines") or []
            cuisine_hint = cuisines[0] if cuisines else "your preferences"
            recommendations.append(
                {
                    "restaurant_id": rid,
                    "rank": rank,
                    "explanation": (
                        f"Strong match for {cuisine_hint} with rating "
                        f"{item.get('rating')} in your search area."
                    ),
                    "match_highlights": [cuisine_hint, "high rating"],
                }
            )

        return json.dumps(
            {
                "summary": "Mock LLM ranked top candidates by fit.",
                "recommendations": recommendations,
            }
        )


def get_llm_client(provider: str | None = None) -> LLMClient:
    """Factory for configured LLM client."""
    name = (provider or LLM_PROVIDER).lower().strip()

    if name == "groq":
        return GroqClient()
    if name in ("mock", "test"):
        return MockLLMClient()
    raise LLMClientError(f"Unsupported LLM_PROVIDER: {name}")


def _extract_candidates_from_messages(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = message.get("content", "")
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'"candidates"\s*:\s*(\[.*?\])', content, re.DOTALL)
            if not match:
                continue
            try:
                payload = {"candidates": json.loads(match.group(1))}
            except json.JSONDecodeError:
                continue
        candidates = payload.get("candidates")
        if isinstance(candidates, list):
            return candidates
    return []
