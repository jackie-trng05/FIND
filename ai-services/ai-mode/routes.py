import os
from pathlib import Path

from flask import Blueprint, request
from openai import OpenAI


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

PROMPT_DIR = Path(__file__).resolve().parent / "prompts" / "implementation"

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

ai_mode_bp = Blueprint("ai_mode", __name__)


def load_prompt(filename):
    return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()


def _chat(messages, max_tokens=300):
    response = client.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.2,
    )
    return response.choices[0].message.content


@ai_mode_bp.post("/ask")
def ask():
    question = request.form.get("question", "").strip()
    if not question:
        return "<p>Question is required.</p>", 400

    try:
        answer = _chat(
            [
                {"role": "system", "content": load_prompt("system_prompt.txt")},
                {"role": "user", "content": question},
            ],
            max_tokens=250,
        )
        return f"<p>{answer}</p>", 200
    except Exception as exc:
        return (
            "<p>Local AI agent request failed. "
            "Check that Ollama is running and that the model is installed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@ai_mode_bp.post("/ask-with-context")
def ask_with_context():
    question = request.form.get("question", "").strip()
    if not question:
        return "<p>Question is required.</p>", 400

    final_prompt = (
        f"{load_prompt('task_prompt.txt')}\n\n"
        f"{load_prompt('context_prompt.txt')}\n\n"
        f"User Question:\n\n{question}"
    )

    try:
        answer = _chat(
            [
                {"role": "system", "content": load_prompt("system_prompt.txt")},
                {"role": "user", "content": final_prompt},
            ],
            max_tokens=350,
        )
        return f"<p>{answer}</p>", 200
    except Exception as exc:
        return (
            "<p>Context-aware request failed. "
            "Check that Ollama is running and that the model is installed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )
