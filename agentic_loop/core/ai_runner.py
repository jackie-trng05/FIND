import os

from openai import OpenAI


def _truncate_words(text: str, limit: int = 60) -> str:
    words = " ".join(text.split()).split()
    if len(words) <= limit:
        return " ".join(words)
    return " ".join(words[:limit]) + " ..."


class AIRunner:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self.implementation_model = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
        # Falls back to the implementation model so the loop works with a single
        # local model; override with OLLAMA_REVIEW_MODEL to use a stronger reviewer.
        self.review_model = os.getenv("OLLAMA_REVIEW_MODEL", self.implementation_model)
        self.client = OpenAI(base_url=self.base_url, api_key="ollama", timeout=180.0)

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        review: bool = False,
        max_tokens: int = 200,
    ) -> tuple[str | None, str | None]:
        model_name = self.review_model if review else self.implementation_model
        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.1,
            )
            content = (response.choices[0].message.content or "").strip()
            if not content:
                return "No response generated.", None
            return _truncate_words(content), None
        except Exception as exc:  # noqa: BLE001 - loop must survive a missing runtime
            return None, f"Model call failed ({model_name}): {exc}"
