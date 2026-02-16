"""Translation and language detection for cross-language snippet indexing."""
from __future__ import annotations

import logging
from openai import AzureOpenAI, OpenAI

from .config import Settings, get_settings

logger = logging.getLogger(__name__)

# Language code to full name mapping
LANGUAGE_NAMES = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "it": "Italian",
    "es": "Spanish",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "ru": "Russian",
    "ja": "Japanese",
    "zh": "Chinese",
    "ko": "Korean",
}


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
        api_key="ollama",
    )


def _resolve_provider(settings: Settings) -> str:
    if settings.llm_provider == "azure":
        return "azure" if (settings.azure_openai_api_key and settings.azure_openai_endpoint) else "none"
    if settings.llm_provider == "ollama":
        return "ollama"
    if settings.llm_provider == "none":
        return "none"
    if settings.azure_openai_api_key and settings.azure_openai_endpoint:
        return "azure"
    return "ollama"


def detect_language(text: str, settings: Settings | None = None) -> str:
    """Detect the language of a text. Returns ISO 639-1 code (e.g., 'en', 'de', 'fr').
    Uses langdetect library first, falls back to LLM if needed."""
    if not text or not text.strip():
        return "en"  # default

    # Try langdetect first (fast, no API calls)
    try:
        from langdetect import detect, LangDetectException
        detected = detect(text[:1000])  # Use first 1000 chars for speed
        return detected.lower()
    except LangDetectException:
        pass
    except ImportError:
        logger.warning("langdetect not installed, falling back to LLM for language detection")

    # Fallback to LLM
    settings = settings or get_settings()
    provider = _resolve_provider(settings)
    if provider == "none":
        return "en"

    prompt = (
        "Detect the language of the following text. "
        "Respond with ONLY the ISO 639-1 language code (e.g., 'en' for English, 'de' for German, 'fr' for French, 'it' for Italian). "
        "Do not include any other text.\n\n"
        f"Text: {text[:500]}"
    )

    if provider == "azure":
        client = _client_azure(settings)
        if client:
            try:
                r = client.chat.completions.create(
                    model=settings.azure_openai_chat_deployment,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=10,
                )
                if r.choices and r.choices[0].message.content:
                    return r.choices[0].message.content.strip().lower()[:2]
            except Exception as e:
                logger.warning("Language detection (Azure) failed: %s", e)

    if provider == "ollama":
        client = _client_ollama(settings)
        try:
            r = client.chat.completions.create(
                model=settings.ollama_chat_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
            )
            if r.choices and r.choices[0].message.content:
                return r.choices[0].message.content.strip().lower()[:2]
        except Exception as e:
            logger.warning("Language detection (Ollama) failed: %s", e)

    return "en"


def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
    settings: Settings | None = None,
) -> str | None:
    """Translate text from source language to target language using LLM.
    Returns translated text or None if translation fails."""
    if not text or not text.strip():
        return None
    if source_lang == target_lang:
        return text  # No translation needed

    settings = settings or get_settings()
    provider = _resolve_provider(settings)
    if provider == "none":
        logger.warning("No LLM provider available for translation")
        return None

    source_name = LANGUAGE_NAMES.get(source_lang, source_lang)
    target_name = LANGUAGE_NAMES.get(target_lang, target_lang)

    system = (
        f"You are a professional translator. Translate the following text from {source_name} to {target_name}. "
        "Preserve the meaning, tone, and formatting of the original text. "
        "Output ONLY the translated text, no explanations or notes."
    )
    user = text

    if provider == "azure":
        client = _client_azure(settings)
        if client:
            try:
                r = client.chat.completions.create(
                    model=settings.azure_openai_chat_deployment,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=len(text) * 2,  # Allow for expansion
                )
                if r.choices and r.choices[0].message.content:
                    return r.choices[0].message.content.strip()
            except Exception as e:
                logger.warning("Translation (Azure) failed: %s", e)
                return None

    if provider == "ollama":
        client = _client_ollama(settings)
        try:
            r = client.chat.completions.create(
                model=settings.ollama_chat_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=len(text) * 2,
            )
            if r.choices and r.choices[0].message.content:
                return r.choices[0].message.content.strip()
        except Exception as e:
            logger.warning("Translation (Ollama) failed: %s", e)
            return None

    return None


def get_translations(
    text: str,
    source_lang: str | None = None,
    target_languages: list[str] | None = None,
    settings: Settings | None = None,
) -> dict[str, str]:
    """Get translations of text to multiple target languages.
    
    Args:
        text: The text to translate
        source_lang: Source language code (auto-detected if None)
        target_languages: List of target language codes (from settings if None)
        settings: App settings
    
    Returns:
        Dict mapping language code to translated text.
        Includes original text under its source language.
        Only includes successful translations.
    """
    settings = settings or get_settings()
    
    if not text or not text.strip():
        return {}

    # Detect source language if not provided
    if not source_lang:
        source_lang = detect_language(text, settings)

    # Get target languages from settings if not provided
    if not target_languages:
        target_languages = settings.get_translation_languages()

    result = {source_lang: text}  # Always include original

    # Translate to each target language (skip source language)
    for target_lang in target_languages:
        if target_lang == source_lang:
            continue
        translated = translate_text(text, source_lang, target_lang, settings)
        if translated:
            result[target_lang] = translated
        else:
            logger.warning(
                "Failed to translate from %s to %s, skipping",
                source_lang,
                target_lang,
            )

    return result


def is_translation_enabled(settings: Settings | None = None) -> bool:
    """Check if translation indexing is enabled and LLM is available."""
    settings = settings or get_settings()
    if not settings.enable_translation_indexing:
        return False
    provider = _resolve_provider(settings)
    return provider != "none"
