"""Loads prompt templates for the Job Posting AI-Mode."""

from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(filename: str) -> str:
    return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()
