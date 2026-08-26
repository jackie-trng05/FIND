"""Ollama (OpenAI-compatible) client and screening text helpers.

Hosts the local LLM client used by AI-Mode candidate screening, plus the
resume-text extraction and response-parsing helpers that surround the call.
"""

import os
from io import BytesIO

from openai import OpenAI

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", timeout=120.0)


def extract_resume_text(data, mimetype):
    text = ""
    mt = (mimetype or "").lower()
    if "pdf" in mt and PdfReader is not None:
        try:
            reader = PdfReader(BytesIO(data))
            pages = []
            for page in reader.pages[:10]:
                try:
                    pages.append(page.extract_text() or "")
                except Exception:
                    continue
            text = "\n".join(p.strip() for p in pages if p.strip())
        except Exception:
            text = ""
    if not text:
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = ""
    text = text.strip()
    if len(text) > 4000:
        text = text[:4000] + "\n[...truncated...]"
    return text


def parse_screening_response(text):
    """Parse LLM output into {Recommendation, Reasoning}."""
    recommendation = "No"
    reasoning_lines = []
    current = None
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("recommendation"):
            after = line.split(":", 1)[1].strip() if ":" in line else ""
            token = after.split()[0] if after else ""
            token_lc = token.lower().strip(".,!?")
            if token_lc.startswith("yes"):
                recommendation = "Yes"
            else:
                recommendation = "No"
            current = None
        elif low.startswith("reasoning"):
            after = line.split(":", 1)[1].strip() if ":" in line else ""
            if after:
                reasoning_lines.append(after)
            current = "reasoning"
        else:
            if current == "reasoning":
                reasoning_lines.append(line)
            elif not reasoning_lines:
                reasoning_lines.append(line)
    reasoning = " ".join(reasoning_lines).strip()
    if len(reasoning) > 800:
        reasoning = reasoning[:800].rstrip() + "…"
    return {"Recommendation": recommendation, "Reasoning": reasoning}
