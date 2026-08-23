"""Resume text extraction utilities.

The AI screening endpoint wants a plain-text view of the candidate's resume
so the LLM can compare it against the job requirements. We support PDF
uploads via pypdf. DOCX and other formats gracefully fall back to a short
placeholder so the AI still receives a well-formed prompt.
"""

from __future__ import annotations

from io import BytesIO

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover - pypdf is a required dep in prod
    PdfReader = None  # type: ignore


_MAX_CHARS = 4000


def extract_text(data: bytes, mimetype: str) -> str:
    """Return a text snippet for the given resume bytes.

    Truncates to ~4000 characters to keep the LLM prompt small.
    """
    text = ""
    mt = (mimetype or "").lower()
    if "pdf" in mt and PdfReader is not None:
        try:
            reader = PdfReader(BytesIO(data))
            pages = []
            for page in reader.pages[:10]:  # cap at 10 pages
                try:
                    pages.append(page.extract_text() or "")
                except Exception:
                    continue
            text = "\n".join(p.strip() for p in pages if p.strip())
        except Exception:
            text = ""
    if not text:
        # Best-effort decode for text/plain, or a fallback stub for docx/etc.
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = ""

    text = text.strip()
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS] + "\n[...truncated...]"
    return text
