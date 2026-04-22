"""vLLM client — wraps the OpenAI-compatible endpoint hosted via Cloudflare tunnel."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from configs.config import ai_config, settings

_llm_cfg: dict = ai_config.get("llm", {})
_DEFAULT_MODEL: str = _llm_cfg.get("default_model", "cyankiwi/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit")
_PROFILES: dict[str, str] = _llm_cfg.get("profiles", {
    "primary": _DEFAULT_MODEL,
    "classifier": _DEFAULT_MODEL,
    "summarizer": _DEFAULT_MODEL,
})
_BASE_URL: str = _llm_cfg.get("base_url", "")
_TIMEOUT: float = _llm_cfg.get("timeout", 60.0)


class VLLMClient:
    """Async HTTP client for the vLLM OpenAI-compatible API."""

    def __init__(
        self,
        model: str,
        base_url: str = _BASE_URL,
        api_key: str = settings.LLM_API_KEY,
        timeout: float = _TIMEOUT,
    ) -> None:
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs,
        }
        response = await self._client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs,
        }
        async with self._client.stream("POST", "/v1/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[len("data: "):]
                if data.strip() == "[DONE]":
                    break
                chunk = json.loads(data)
                delta = chunk["choices"][0].get("delta", {})
                if content := delta.get("content"):
                    yield content

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "VLLMClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()


def create_llm(
    profile: str = "primary",
    base_url: str = _BASE_URL,
    api_key: str = settings.LLM_API_KEY,
) -> VLLMClient:
    """Factory used in app lifespan: create_llm(profile='primary')."""
    model = _PROFILES.get(profile, _DEFAULT_MODEL)
    return VLLMClient(model=model, base_url=base_url, api_key=api_key)
