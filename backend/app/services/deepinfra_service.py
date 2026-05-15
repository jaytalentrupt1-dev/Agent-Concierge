from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


DEEPINFRA_BASE_URL = "https://api.deepinfra.com/v1/openai"


class DeepInfraChatClient:
    """Small OpenAI-compatible DeepInfra chat client for Conci AI.

    The caller is responsible for role-filtering app data before asking this
    client to rewrite an answer. Intent classification sends only the user's
    message and the allowed intent ids.
    """

    mode = "deepinfra_chat_completions"

    def __init__(self, api_key: str, model: str = "deepseek-ai/DeepSeek-V3", base_url: str = DEEPINFRA_BASE_URL):
        self.api_key = api_key.strip()
        self.model = model.strip() or "deepseek-ai/DeepSeek-V3"
        self.base_url = base_url.rstrip("/")

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2, max_tokens: int = 700) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            response_data = json.loads(response.read().decode("utf-8"))
        choices = response_data.get("choices") or []
        if not choices:
            raise RuntimeError("DeepInfra response did not include choices.")
        message = choices[0].get("message") or {}
        content = str(message.get("content") or "").strip()
        if not content:
            raise RuntimeError("DeepInfra response did not include content.")
        return content

    def classify_intent(self, message: str, allowed_intents: list[str]) -> dict[str, Any]:
        system = (
            "You classify Conci AI user messages. Return strict JSON only. "
            "Do not answer the user. Use only one of the allowed intent ids. "
            "Choose intent from the full sentence meaning and previous-topic hints, not isolated words. "
            "Important distinctions: calendar events means calendar_events, today's date means utility_date, "
            "ticket history means recent_tickets, a specific ticket status question means ticket_status, "
            "food vendor details means vendor_details, vendor billing means vendor_billing, "
            "and clarifications like show more, give all, only food, or earlier history should continue the previous topic."
        )
        user = {
            "allowed_intents": allowed_intents,
            "message": message,
            "schema": {
                "intent": "string",
                "confidence": "number between 0 and 1",
                "entities": "object",
                "required_role_scope": "string",
                "action_type": "answer|create|update|fetch|utility",
                "missing_fields": "array of strings",
                "confirmation_required": "boolean",
            },
        }
        content = self.chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user)},
            ],
            temperature=0,
            max_tokens=500,
        )
        parsed = parse_json_object(content)
        intent = str(parsed.get("intent") or "").strip().lower()
        if intent not in allowed_intents:
            return {}
        return parsed

    def refine_response(self, question: str, response: dict[str, Any]) -> dict[str, Any]:
        system = (
            "You are Conci AI, a smart assistant for admin, IT, finance, and employee workflows. "
            "Rewrite the supplied answer for clarity. Use only the supplied answer and bullets. "
            "Do not add facts, rows, totals, names, or data. Return strict JSON only with keys answer and bullets."
        )
        user = {
            "question": question,
            "answer": response.get("answer") or "",
            "bullets": response.get("bullets") or [],
            "source": response.get("source") or "",
        }
        content = self.chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user)},
            ],
            temperature=0.2,
            max_tokens=700,
        )
        parsed = parse_json_object(content)
        answer = str(parsed.get("answer") or response.get("answer") or "").strip()
        bullets = parsed.get("bullets") if isinstance(parsed.get("bullets"), list) else response.get("bullets", [])
        return {
            "answer": answer,
            "bullets": [str(item) for item in bullets],
        }


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {}
        try:
            parsed = json.loads(text[start:end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def deepinfra_api_key_is_placeholder(value: str) -> bool:
    return value.strip() in {
        "PASTE_YOUR_DEEPINFRA_API_KEY_HERE",
        "your-deepinfra-api-key",
        "your_deepinfra_api_key",
    }


def get_deepinfra_client(settings: Any) -> DeepInfraChatClient | None:
    provider = str(getattr(settings, "ai_provider", "") or "").strip().lower()
    api_key = str(getattr(settings, "deepinfra_api_key", "") or "").strip()
    if provider != "deepinfra" or not api_key or deepinfra_api_key_is_placeholder(api_key):
        return None
    model = str(getattr(settings, "deepinfra_model", "") or "deepseek-ai/DeepSeek-V3")
    return DeepInfraChatClient(api_key=api_key, model=model)
