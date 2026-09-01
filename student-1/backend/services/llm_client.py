"""Ollama (OpenAI-compatible) client for the Profile AI-Mode.

Uses the approved open-source LLM through the local Ollama runtime, following
the same pattern as the other students' AI-Mode integrations.
"""

from io import BytesIO

from openai import OpenAI

from services.config import OLLAMA_BASE_URL, OLLAMA_MODEL

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", timeout=120.0)

# Below this many characters of extracted text, treat the resume as "too short"
# rather than trust a small local model to accurately self-report the issue.
MIN_RESUME_CHARS = 120


def extract_resume_text(data: bytes, mimetype: str) -> str:
    """Best-effort text extraction from a resume file. Returns "" on failure."""
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


def classify_resume_quality(text: str) -> str:
    """Deterministically classify extracted resume text.

    Returns "unreadable" when extraction produced no usable text (the file
    itself couldn't be read, e.g. a scanned image), "short" when some text
    was extracted but there isn't much of it, or "ok" otherwise. Doing this
    in code -- rather than asking the model to self-report -- avoids relying
    on a small local model to accurately diagnose why it's being generic.
    """
    if not text or not text.strip():
        return "unreadable"
    if len(text.strip()) < MIN_RESUME_CHARS:
        return "short"
    return "ok"


def parse_profile_suggestions(text: str) -> dict:
    """Parse the model's labeled-line response into the expected fields.

    Expected format (one label per line, any order)::

        Professional_Title: ...
        Summary: ...
        Interests: ...
        Note: ...

    Missing/unparsed fields default to "". Unlabelled continuation lines are
    appended to whichever field was last seen, so wrapped sentences aren't lost.
    A small model often writes a literal placeholder (e.g. "None", "N/A")
    instead of actually leaving a field blank -- those are normalised to "".
    """
    _BLANK_TOKENS = {"none", "n/a", "na", "null", "-", "not applicable", "blank"}

    fields = {"professional_title": "", "summary": "", "interests": "", "note": ""}
    current = None
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if ":" in line:
            label, _, rest = line.partition(":")
            key = label.strip().lower().replace(" ", "_")
            if key in fields:
                current = key
                fields[current] = rest.strip()
                continue
        if current:
            fields[current] = (fields[current] + " " + line).strip()

    for key, value in fields.items():
        if value.strip().lower().rstrip(".") in _BLANK_TOKENS:
            fields[key] = ""
    return fields
