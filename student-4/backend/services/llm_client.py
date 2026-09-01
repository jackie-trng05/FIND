from openai import OpenAI

from services.config import OLLAMA_BASE_URL, OLLAMA_MODEL

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


def create_chat_completion(messages, max_tokens=300, temperature=0.2, model=None):
    response = client.chat.completions.create(
        model=model or OLLAMA_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content
