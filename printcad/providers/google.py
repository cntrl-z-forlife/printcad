from __future__ import annotations

import uuid
from typing import Any

import httpx

from printcad.providers.base import LLMResponse, Provider, ToolCall
from printcad.providers.openai_compat import raise_httpx, http_timeout


class GoogleProvider(Provider):
    name = "google"
    kind = "google"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> LLMResponse:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload: dict[str, Any] = {
            "contents": messages,
            "generationConfig": {"temperature": 0.2},
        }
        if tools:
            payload["tools"] = tools
        with httpx.Client(timeout=http_timeout()) as client:
            try:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
            except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                raise_httpx(exc)
            data = resp.json()
        cand = (data.get("candidates") or [{}])[0]
        parts = ((cand.get("content") or {}).get("parts")) or []
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        for part in parts:
            if "text" in part:
                text_parts.append(part.get("text") or "")
            fc = part.get("functionCall")
            if fc:
                calls.append(
                    ToolCall(
                        id=uuid.uuid4().hex,
                        name=fc.get("name") or "",
                        arguments=fc.get("args") or {},
                    )
                )
        return LLMResponse(text="\n".join(text_parts), tool_calls=calls, raw=data)

    def format_tool_result(self, call: ToolCall, result: str) -> dict[str, Any]:
        return {
            "role": "user",
            "parts": [
                {
                    "functionResponse": {
                        "name": call.name,
                        "response": {"result": result},
                    }
                }
            ],
        }


def google_contents(system: str, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    if system:
        contents.append({"role": "user", "parts": [{"text": f"SYSTEM:\n{system}"}]})
        contents.append({"role": "model", "parts": [{"text": "Understood. I will use the tools."}]})
    contents.extend(history)
    return contents


def assistant_function_message(response: LLMResponse) -> dict[str, Any]:
    parts: list[dict[str, Any]] = []
    if response.text:
        parts.append({"text": response.text})
    for call in response.tool_calls:
        parts.append({"functionCall": {"name": call.name, "args": call.arguments}})
    return {"role": "model", "parts": parts}
