"""Answer generation using Azure OpenAI or Ollama (local)."""
from __future__ import annotations

import logging
from openai import AzureOpenAI, OpenAI

from .config import Settings, get_settings

logger = logging.getLogger(__name__)


def _client_azure(settings: Settings) -> AzureOpenAI | None:
    if not settings.azure_openai_api_key or not settings.azure_openai_endpoint:
        return None
    return AzureOpenAI(
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint,
    )


def _client_ollama(settings: Settings) -> OpenAI | None:
    return OpenAI(
        base_url=settings.ollama_base_url.rstrip("/") + "/v1",
        api_key="ollama",  # Ollama does not require a key
    )


def _resolve_provider(settings: Settings) -> str:
    if settings.llm_provider == "azure":
        return "azure" if (settings.azure_openai_api_key and settings.azure_openai_endpoint) else "none"
    if settings.llm_provider == "ollama":
        return "ollama"
    if settings.llm_provider == "none":
        return "none"
    # auto: prefer Azure, then Ollama
    if settings.azure_openai_api_key and settings.azure_openai_endpoint:
        return "azure"
    return "ollama"


def generate_answer(question: str, snippet_texts: list[str], settings: Settings | None = None) -> str:
    """Generate an answer from question and retrieved snippets using Azure OpenAI or Ollama. Fallback to top snippet if no LLM."""
    settings = settings or get_settings()
    provider = _resolve_provider(settings)

    if not snippet_texts:
        return "No relevant snippets found."

    snippets_block = "\n\n".join(f"[{i+1}] {t}" for i, t in enumerate(snippet_texts))
    system = (
        "Answer the user's question using ONLY the provided numbered snippets. "
        "Be concise. Do not invent information. If the snippets do not contain the answer, say so."
    )
    user = f"Question: {question}\n\nSnippets:\n{snippets_block}"

    if provider == "azure":
        client = _client_azure(settings)
        if client:
            try:
                r = client.chat.completions.create(
                    model=settings.azure_openai_chat_deployment,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    max_tokens=500,
                )
                if r.choices and r.choices[0].message.content:
                    return r.choices[0].message.content.strip()
            except Exception as e:
                logger.warning("Azure OpenAI call failed: %s", e)
        # fallback
        return snippet_texts[0]

    if provider == "ollama":
        client = _client_ollama(settings)
        try:
            r = client.chat.completions.create(
                model=settings.ollama_chat_model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=500,
            )
            if r.choices and r.choices[0].message.content:
                return r.choices[0].message.content.strip()
        except Exception as e:
            logger.warning("Ollama call failed (is Ollama running?): %s", e)

    # no LLM or both failed: return top snippet
    return snippet_texts[0]
