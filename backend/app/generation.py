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


def _parse_answer_and_sections(raw: str, num_sources: int) -> tuple[str, list[str | None]]:
    """Extract answer and optional section labels from LLM output. Expects 'SECTIONS:' followed by one line per source."""
    raw = (raw or "").strip()
    sections: list[str | None] = []
    answer = raw
    marker = "SECTIONS:"
    idx = raw.upper().find(marker.upper())
    if idx >= 0:
        answer = raw[:idx].strip()
        rest = raw[idx + len(marker) :].strip()
        lines = [line.strip() for line in rest.split("\n") if line.strip()][:num_sources]
        sections = [lines[i] if i < len(lines) else None for i in range(num_sources)]
    else:
        sections = [None] * num_sources
    return answer, sections


def _closeness_system_instruction(closeness: float) -> str:
    """Return system instruction fragment for answer_closeness (0=free, 1=word-for-word)."""
    if closeness < 0.3:
        return (
            "Use the provided snippets as inspiration only. You may answer freely and rephrase; "
            "do not restrict yourself to the exact wording."
        )
    if closeness > 0.7:
        return (
            "Your answer MUST stay as close as possible to the exact wording of the snippets. "
            "Prefer quoting and paraphrasing; do not add new formulations or information not in the snippets."
        )
    return (
        "Formulate your answer closely based on the snippets; light rephrasing is allowed. "
        "Do not add information that is not present in the snippets."
    )


def generate_answer(
    question: str,
    snippet_texts: list[str],
    settings: Settings | None = None,
    answer_closeness: float = 0.5,
) -> tuple[str, list[str | None]]:
    """Generate an answer and per-source section labels from question and retrieved snippets.
    Returns (answer_text, section_labels). section_labels[i] is a short section/context for snippet i, or None.
    answer_closeness: 0=free, 1=stick to snippet wording."""
    settings = settings or get_settings()
    provider = _resolve_provider(settings)
    num_sources = len(snippet_texts)

    if not snippet_texts:
        return "No relevant snippets found.", []

    snippets_block = "\n\n".join(f"[{i+1}] {t}" for i, t in enumerate(snippet_texts))
    closeness_instruction = _closeness_system_instruction(answer_closeness)
    system = (
        "You are a helpful assistant that writes polite, casual email replies in the same language as the user's input. "
        "Answer the user's question using the provided numbered snippets. "
        f"{closeness_instruction} "
        "IMPORTANT formatting rules:\n"
        "1. Try to extract the sender's name from the input text. First look for a 'Von:'/'From:' line or email signature. "
        "If not found, fall back to the name used in the greeting/salutation of the input (e.g. 'Lieber Herr Meier' → the sender signed or was addressed as 'Meier'). "
        "Use the LAST NAME with a formal title: 'Sehr geehrter Herr [Nachname],' / 'Sehr geehrte Frau [Nachname],' "
        "(or 'Dear Mr [Last name],' / 'Dear Ms [Last name],' in English). "
        "If no name can be extracted at all, use a generic greeting like 'Sehr geehrte Damen und Herren,' or 'Dear Sir or Madam,'.\n"
        "2. Write the body in a polite, friendly, and casual tone — as if replying to a colleague. "
        "Be concise but helpful. The answer should be ready to copy-paste as an email response.\n"
        "3. End with a friendly closing (e.g. 'Viele Grüße' or 'Best regards' depending on the language).\n"
        "4. If the snippets do not contain the answer, politely say so.\n"
        "5. After your complete email, on a new line write exactly SECTIONS: and then one line per snippet in order (snippet 1, 2, ...): "
        "a very short section or context for each snippet (e.g. 'Scrum Roles - Product Owner' or 'Definition of Done'). "
        "One line per snippet, no numbers or bullets."
    )
    user = f"Question / incoming message:\n{question}\n\nSnippets:\n{snippets_block}"

    if provider == "azure":
        client = _client_azure(settings)
        if client:
            try:
                r = client.chat.completions.create(
                    model=settings.azure_openai_chat_deployment,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    max_tokens=800,
                )
                if r.choices and r.choices[0].message.content:
                    return _parse_answer_and_sections(r.choices[0].message.content.strip(), num_sources)
            except Exception as e:
                logger.warning("Azure OpenAI call failed: %s", e)
        return snippet_texts[0], [None] * num_sources

    if provider == "ollama":
        client = _client_ollama(settings)
        try:
            r = client.chat.completions.create(
                model=settings.ollama_chat_model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=800,
            )
            if r.choices and r.choices[0].message.content:
                return _parse_answer_and_sections(r.choices[0].message.content.strip(), num_sources)
        except Exception as e:
            logger.warning("Ollama call failed (is Ollama running?): %s", e)

    return snippet_texts[0], [None] * num_sources


def refine_answer(
    original_question: str,
    original_answer: str,
    refinement_prompt: str,
    snippet_texts: list[str],
    settings: Settings | None = None,
    answer_closeness: float = 0.5,
) -> str:
    """Refine an existing answer based on user feedback and selected snippets.
    Returns the refined answer text."""
    settings = settings or get_settings()
    provider = _resolve_provider(settings)

    if not snippet_texts:
        return original_answer  # Can't refine without context

    snippets_block = "\n\n".join(f"[{i+1}] {t}" for i, t in enumerate(snippet_texts))
    closeness_instruction = _closeness_system_instruction(answer_closeness)

    system = (
        "You are refining an existing email reply based on user feedback. "
        f"{closeness_instruction} "
        "Use the provided snippets as context. "
        "Keep the polite, casual email tone of the original answer. "
        "The refined answer must remain a ready-to-paste email reply with greeting and closing. "
        "Produce only the improved email reply without any explanations or meta-commentary."
    )
    user = (
        f"Original Question / incoming message: {original_question}\n\n"
        f"Original Email Reply: {original_answer}\n\n"
        f"User's refinement request: {refinement_prompt}\n\n"
        f"Context snippets to use:\n{snippets_block}\n\n"
        "Please provide the refined email reply:"
    )

    if provider == "azure":
        client = _client_azure(settings)
        if client:
            try:
                r = client.chat.completions.create(
                    model=settings.azure_openai_chat_deployment,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    max_tokens=800,
                )
                if r.choices and r.choices[0].message.content:
                    return r.choices[0].message.content.strip()
            except Exception as e:
                logger.warning("Azure OpenAI refine call failed: %s", e)
        return original_answer

    if provider == "ollama":
        client = _client_ollama(settings)
        try:
            r = client.chat.completions.create(
                model=settings.ollama_chat_model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=800,
            )
            if r.choices and r.choices[0].message.content:
                return r.choices[0].message.content.strip()
        except Exception as e:
            logger.warning("Ollama refine call failed: %s", e)

    return original_answer


def generate_hypothetical_answer(question: str, settings: Settings | None = None) -> str:
    """Generate a short hypothetical answer (1-2 sentences) for HyDE retrieval. Returns empty string if no LLM."""
    settings = settings or get_settings()
    provider = _resolve_provider(settings)
    if provider == "none":
        return ""

    prompt = (
        "Answer the following question in 1-2 short sentences, without using any external sources. "
        "Be concise and direct.\n\nQuestion: "
    ) + question

    if provider == "azure":
        client = _client_azure(settings)
        if client:
            try:
                r = client.chat.completions.create(
                    model=settings.azure_openai_chat_deployment,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                )
                if r.choices and r.choices[0].message.content:
                    return (r.choices[0].message.content or "").strip()
            except Exception as e:
                logger.warning("HyDE hypothetical answer (Azure) failed: %s", e)
        return ""

    if provider == "ollama":
        client = _client_ollama(settings)
        try:
            r = client.chat.completions.create(
                model=settings.ollama_chat_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
            )
            if r.choices and r.choices[0].message.content:
                return (r.choices[0].message.content or "").strip()
        except Exception as e:
            logger.warning("HyDE hypothetical answer (Ollama) failed: %s", e)

    return ""


def generate_example_question(
    snippet_text: str,
    snippet_title: str | None = None,
    settings: Settings | None = None,
) -> str:
    """Generate an example question that this snippet could answer (reverse HyDE).
    
    This is useful for hybrid retrieval - by embedding example questions,
    we can match user questions directly against them.
    
    Args:
        snippet_text: The snippet content to generate a question for
        snippet_title: Optional title for additional context
        settings: App settings
    
    Returns:
        A question string, or empty string if LLM is unavailable
    """
    settings = settings or get_settings()
    provider = _resolve_provider(settings)
    if provider == "none":
        return ""
    
    # Truncate text if too long to fit in context
    max_text_len = 2000
    text_for_prompt = snippet_text[:max_text_len]
    if len(snippet_text) > max_text_len:
        text_for_prompt += "..."
    
    title_context = f" titled '{snippet_title}'" if snippet_title else ""
    
    system = (
        "You generate example questions for a knowledge base. "
        "Given a text snippet, generate ONE clear, natural question that this snippet would answer. "
        "The question should be something a user might actually ask. "
        "Be concise - output only the question, no explanations or prefixes."
    )
    
    user = (
        f"Generate one example question that the following snippet{title_context} would answer:\n\n"
        f"---\n{text_for_prompt}\n---\n\n"
        "Question:"
    )
    
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
                    max_tokens=100,
                )
                if r.choices and r.choices[0].message.content:
                    question = (r.choices[0].message.content or "").strip()
                    # Clean up common prefixes
                    for prefix in ["Question:", "Q:", "Example question:"]:
                        if question.lower().startswith(prefix.lower()):
                            question = question[len(prefix):].strip()
                    return question
            except Exception as e:
                logger.warning("Generate example question (Azure) failed: %s", e)
        return ""
    
    if provider == "ollama":
        client = _client_ollama(settings)
        try:
            r = client.chat.completions.create(
                model=settings.ollama_chat_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=100,
            )
            if r.choices and r.choices[0].message.content:
                question = (r.choices[0].message.content or "").strip()
                # Clean up common prefixes
                for prefix in ["Question:", "Q:", "Example question:"]:
                    if question.lower().startswith(prefix.lower()):
                        question = question[len(prefix):].strip()
                return question
        except Exception as e:
            logger.warning("Generate example question (Ollama) failed: %s", e)
    
    return ""
