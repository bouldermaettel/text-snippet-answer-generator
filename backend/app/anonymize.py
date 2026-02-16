"""PII anonymization using LLM (Azure OpenAI or Ollama).

Replaces sensitive data (names, addresses, company names, phone numbers,
email addresses, etc.) with generic placeholders like [NAME], [ADDRESS],
[COMPANY], [PHONE], [EMAIL], etc.
"""
from __future__ import annotations

import logging
import re

from .config import Settings, get_settings
from .generation import _client_azure, _client_ollama, _resolve_provider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a data anonymization assistant. Your task is to replace all personally \
identifiable information (PII) in the given text with generic placeholders.

Replace the following types of sensitive data:
- Person names (first, last, full) -> [NAME]
- Company / organization names -> [COMPANY]
- Street addresses, cities, ZIP codes -> [ADDRESS]
- Phone numbers -> [PHONE]
- Email addresses -> [EMAIL]
- Dates of birth -> [DOB]
- Social security / ID numbers -> [ID_NUMBER]
- Bank account / IBAN numbers -> [ACCOUNT]
- Credit card numbers -> [CREDIT_CARD]
- License plate numbers -> [LICENSE_PLATE]
- Website URLs that identify a specific person or company -> [URL]

Important rules:
1. Keep the rest of the text EXACTLY as-is (same language, formatting, line breaks).
2. Do NOT add explanations, comments, or metadata.
3. Do NOT remove or summarize any non-PII content.
4. If multiple different persons appear, use [NAME_1], [NAME_2], etc.
5. If multiple different companies appear, use [COMPANY_1], [COMPANY_2], etc.
6. Generic terms (e.g. "the customer", "the applicant") are NOT PII - leave them.
7. Product names, drug names, and technical terms are NOT PII - leave them.
8. Output ONLY the anonymized text, nothing else.\
"""

_USER_PROMPT_TEMPLATE = "Anonymize the following text:\n\n{text}"


def anonymize_text(text: str, settings: Settings | None = None) -> str:
    """Replace PII in *text* with generic placeholders using the configured LLM.

    Returns the anonymized text, or the original text unchanged if no LLM is
    available or the call fails.
    """
    if not text or not text.strip():
        return text

    settings = settings or get_settings()
    provider = _resolve_provider(settings)

    if provider == "none":
        logger.warning("PII anonymization requested but no LLM provider available")
        return text

    user_prompt = _USER_PROMPT_TEMPLATE.format(text=text)

    # For very long texts, process in chunks to stay within context limits
    max_chars = 6000
    if len(text) > max_chars:
        return _anonymize_long_text(text, max_chars, settings, provider)

    return _call_llm(user_prompt, settings, provider) or text


def _anonymize_long_text(text: str, max_chars: int, settings: Settings, provider: str) -> str:
    """Split long text into chunks, anonymize each, then reassemble."""
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) + 2 > max_chars and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_len = 0
        current_chunk.append(para)
        current_len += len(para) + 2

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    anonymized_parts: list[str] = []
    for chunk in chunks:
        user_prompt = _USER_PROMPT_TEMPLATE.format(text=chunk)
        result = _call_llm(user_prompt, settings, provider)
        anonymized_parts.append(result if result else chunk)

    return "\n\n".join(anonymized_parts)


def _call_llm(user_prompt: str, settings: Settings, provider: str) -> str | None:
    """Send the anonymization request to the LLM. Returns anonymized text or None on failure."""

    if provider == "azure":
        client = _client_azure(settings)
        if client:
            try:
                r = client.chat.completions.create(
                    model=settings.azure_openai_chat_deployment,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=2000,
                    temperature=0.0,
                )
                if r.choices and r.choices[0].message.content:
                    return r.choices[0].message.content.strip()
            except Exception as e:
                logger.warning("PII anonymization (Azure) failed: %s", e)
        return None

    if provider == "ollama":
        client = _client_ollama(settings)
        try:
            r = client.chat.completions.create(
                model=settings.ollama_chat_model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=2000,
                temperature=0.0,
            )
            if r.choices and r.choices[0].message.content:
                return r.choices[0].message.content.strip()
        except Exception as e:
            logger.warning("PII anonymization (Ollama) failed: %s", e)

    return None
