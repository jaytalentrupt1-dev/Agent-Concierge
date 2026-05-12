#!/usr/bin/env python3
"""Simple terminal tester for the xAI Grok chat completions API."""

import json
import urllib.error
import urllib.request


XAI_API_KEY = "PASTE_YOUR_GROK_API_KEY_HERE"

API_URL = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-4"
SYSTEM_MESSAGE = "You are Conci AI, a smart assistant for admin, IT, finance, and employee workflows."


def call_grok(messages):
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        response_data = json.loads(response.read().decode("utf-8"))

    choices = response_data.get("choices") or []
    if not choices:
        raise RuntimeError("The API response did not include any choices.")

    message = choices[0].get("message") or {}
    answer = message.get("content")
    if not answer:
        raise RuntimeError("The API response did not include an answer.")

    return answer


def format_api_error(error):
    if isinstance(error, urllib.error.HTTPError):
        body = error.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
            detail = payload.get("error") or payload
        except json.JSONDecodeError:
            detail = body or error.reason
        return f"API error {error.code}: {detail}"

    if isinstance(error, urllib.error.URLError):
        return f"Network error: {error.reason}"

    return f"Error: {error}"


def main():
    if XAI_API_KEY == "PASTE_YOUR_GROK_API_KEY_HERE":
        print("Add your Grok API key to XAI_API_KEY at the top of this file before running.")
        return

    messages = [{"role": "system", "content": SYSTEM_MESSAGE}]
    print("Grok API test. Type 'exit' or 'quit' to stop.\n")

    while True:
        question = input("You: ").strip()
        if question.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break
        if not question:
            continue

        messages.append({"role": "user", "content": question})
        try:
            answer = call_grok(messages)
        except Exception as error:
            messages.pop()
            print(format_api_error(error))
            continue

        messages.append({"role": "assistant", "content": answer})
        print(f"\nGrok: {answer}\n")


if __name__ == "__main__":
    main()
