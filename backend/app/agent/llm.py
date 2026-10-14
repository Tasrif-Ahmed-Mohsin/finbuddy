"""DeepSeek client (OpenAI-compatible chat completions API), via plain httpx.

Choices:
  * model `deepseek-flash` by default, thinking mode DISABLED: we need fast, cheap, predictable
    answers for extraction and tool calls (thinking mode also rejects tool_choice="required").
  * DeepSeek is reachable from mainland China, which matters for the on-site final in Shenzhen.
  * Any failure raises LLMUnavailable; callers always have a deterministic fallback.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date

import httpx

from app.config import Settings


class LLMUnavailable(Exception):
    """The LLM could not be reached or returned something unusable. Never contains secrets."""


@dataclass
class LLMReply:
    content: str | None
    tool_calls: list[dict]
    finish_reason: str | None
    usage: dict

    def tool_call_args(self, call: dict) -> dict:
        """Arguments arrive as a JSON string and may be invalid; validate before use."""
        try:
            args = json.loads(call["function"].get("arguments") or "{}")
        except (json.JSONDecodeError, KeyError, TypeError):
            return {}
        return args if isinstance(args, dict) else {}


class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com", model: str = "deepseek-flash",
                 timeout: float = 30.0, transport: httpx.BaseTransport | None = None, daily_calls: int = 0):
        self._key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._http = httpx.Client(timeout=timeout, transport=transport)
        self.daily_calls = daily_calls  # 0 = no limit; on a public demo server, a budget (SATHI_LLM_DAILY_CALLS)
        self._used: tuple[str, int] = ("", 0)

    def chat(self, messages: list[dict], tools: list[dict] | None = None, json_mode: bool = False,
             max_tokens: int = 1200, temperature: float = 0.2) -> LLMReply:
        body: dict = {
            "model": self.model,
            "messages": messages,
            "thinking": {"type": "disabled"},
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if self.daily_calls:
            today = date.today().isoformat()
            used = self._used[1] if self._used[0] == today else 0
            if used >= self.daily_calls:
                raise LLMUnavailable("daily AI budget reached")  # callers fall back to the rule-based answers
            self._used = (today, used + 1)
        try:
            r = self._http.post(f"{self.base_url}/chat/completions", json=body,
                                headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"})
        except httpx.HTTPError as e:
            raise LLMUnavailable(f"network error: {type(e).__name__}") from None
        if r.status_code != 200:
            raise LLMUnavailable(f"LLM HTTP {r.status_code}")
        try:
            data = r.json()
            choice = data["choices"][0]
            msg = choice["message"]
        except (ValueError, KeyError, IndexError):
            raise LLMUnavailable("malformed LLM response") from None
        return LLMReply(msg.get("content"), msg.get("tool_calls") or [], choice.get("finish_reason"), data.get("usage", {}))

    def chat_json(self, messages: list[dict], max_tokens: int = 800) -> dict:
        reply = self.chat(messages, json_mode=True, max_tokens=max_tokens, temperature=0)
        if not reply.content or not reply.content.strip():
            raise LLMUnavailable("empty JSON content")  # documented occasional DeepSeek behaviour
        try:
            out = json.loads(reply.content)
        except json.JSONDecodeError:
            raise LLMUnavailable("LLM did not return valid JSON") from None
        if not isinstance(out, dict):
            raise LLMUnavailable("LLM JSON is not an object")
        return out


def make_llm(settings: Settings) -> DeepSeekClient | None:
    if not settings.llm_enabled or not settings.deepseek_api_key:
        return None
    return DeepSeekClient(settings.deepseek_api_key, settings.deepseek_base_url, settings.deepseek_model,
                          daily_calls=int(os.environ.get("SATHI_LLM_DAILY_CALLS", "0") or 0))
