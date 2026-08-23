"""Ollama (OpenAI-compatible) client for the Application Screening AI-Mode.

Uses the approved open-source LLM through the local Ollama runtime, following
the reference pattern from the enrolment-app labs.
"""

import os

from openai import OpenAI

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", timeout=120.0)


def create_chat_completion(messages, max_tokens=400, temperature=0.2, model=None) -> str:
    response = client.chat.completions.create(
        model=model or OLLAMA_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return (response.choices[0].message.content or "").strip()
