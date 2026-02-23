"""Prompt template store: persists admin-customised LLM prompts to data/prompts.json."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PromptDef:
    label: str
    description: str
    default: str
    placeholders: list[str] = field(default_factory=list)
    group: str = "Advanced"


PROMPT_DEFAULTS: dict[str, PromptDef] = {
    "answer_generation_system": PromptDef(
        label="Answer Generation – System",
        description="System prompt for the main answer generation. Controls tone, formatting rules, and email structure.",
        group="Main Prompts",
        placeholders=["{closeness_instruction}"],
        default=(
            "You are a helpful assistant that writes polite, casual email replies in the same language as the user's input. "
            "Answer the user's question using the provided numbered snippets. "
            "{closeness_instruction} "
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
        ),
    ),
    "closeness_instruction": PromptDef(
        label="Closeness Instruction",
        description="Instruction injected into generation/refinement prompts to control how closely the answer sticks to snippet wording. The {closeness} placeholder receives a float from 0 (completely free) to 1 (identical wording).",
        group="Main Prompts",
        placeholders=["{closeness}"],
        default=(
            "Stick to the wording of the provided snippets with a closeness level of {closeness} "
            "on a scale from 0 (completely free formulation) to 1 (identical wording). "
            "At 0, use snippets as loose inspiration and rephrase freely. "
            "At 1, quote them verbatim. Interpolate your behaviour accordingly."
        ),
    ),
    "refine_system": PromptDef(
        label="Refinement – System",
        description="System prompt for refining an existing answer based on user feedback.",
        group="Main Prompts",
        placeholders=["{closeness_instruction}"],
        default=(
            "You are refining an existing email reply based on user feedback. "
            "{closeness_instruction} "
            "Use the provided snippets as context. "
            "Keep the polite, casual email tone of the original answer. "
            "The refined answer must remain a ready-to-paste email reply with greeting and closing. "
            "Produce only the improved email reply without any explanations or meta-commentary."
        ),
    ),
    "answer_generation_user": PromptDef(
        label="Answer Generation – User Message",
        description="User message template for answer generation. Structures the question and snippets sent to the LLM.",
        placeholders=["{question}", "{snippets_block}"],
        default="Question / incoming message:\n{question}\n\nSnippets:\n{snippets_block}",
    ),
    "refine_user": PromptDef(
        label="Refinement – User Message",
        description="User message template for answer refinement. Structures the original Q&A, feedback, and snippets.",
        placeholders=["{original_question}", "{original_answer}", "{refinement_prompt}", "{snippets_block}"],
        default=(
            "Original Question / incoming message: {original_question}\n\n"
            "Original Email Reply: {original_answer}\n\n"
            "User's refinement request: {refinement_prompt}\n\n"
            "Context snippets to use:\n{snippets_block}\n\n"
            "Please provide the refined email reply:"
        ),
    ),
    "hyde_user": PromptDef(
        label="HyDE – User Message",
        description="Prompt for generating a short hypothetical answer used in HyDE retrieval.",
        placeholders=["{question}"],
        default=(
            "Answer the following question in 1-2 short sentences, without using any external sources. "
            "Be concise and direct.\n\nQuestion: {question}"
        ),
    ),
    "example_question_system": PromptDef(
        label="Example Question – System",
        description="System prompt for generating example questions from snippets (reverse HyDE).",
        placeholders=[],
        default=(
            "You generate example questions for a knowledge base. "
            "Given a text snippet, generate ONE clear, natural question that this snippet would answer. "
            "The question should be something a user might actually ask. "
            "Be concise - output only the question, no explanations or prefixes."
        ),
    ),
    "example_question_user": PromptDef(
        label="Example Question – User Message",
        description="User message template for generating an example question from a snippet.",
        placeholders=["{title_context}", "{text_for_prompt}"],
        default=(
            "Generate one example question that the following snippet{title_context} would answer:\n\n"
            "---\n{text_for_prompt}\n---\n\n"
            "Question:"
        ),
    ),
}


def _prompts_path() -> Path:
    p = get_settings().data_dir / "prompts.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_overrides() -> dict[str, str]:
    path = _prompts_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if isinstance(v, str)}
    except Exception:
        logger.warning("Failed to read %s, using defaults", path)
    return {}


def _save_overrides(overrides: dict[str, str]) -> None:
    path = _prompts_path()
    path.write_text(json.dumps(overrides, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_prompt(key: str) -> str:
    """Return the current prompt template for *key* (custom override or default)."""
    if key not in PROMPT_DEFAULTS:
        raise KeyError(f"Unknown prompt key: {key}")
    overrides = _load_overrides()
    return overrides.get(key, PROMPT_DEFAULTS[key].default)


def set_prompt(key: str, template: str) -> None:
    """Persist a custom prompt template for *key*."""
    if key not in PROMPT_DEFAULTS:
        raise KeyError(f"Unknown prompt key: {key}")
    overrides = _load_overrides()
    overrides[key] = template
    _save_overrides(overrides)


def reset_prompt(key: str) -> None:
    """Remove custom override for *key*, reverting to the default."""
    if key not in PROMPT_DEFAULTS:
        raise KeyError(f"Unknown prompt key: {key}")
    overrides = _load_overrides()
    if key in overrides:
        del overrides[key]
        _save_overrides(overrides)


def list_prompts() -> list[dict]:
    """Return metadata + current value for every registered prompt."""
    overrides = _load_overrides()
    result: list[dict] = []
    for key, defn in PROMPT_DEFAULTS.items():
        is_default = key not in overrides
        result.append({
            "key": key,
            "label": defn.label,
            "description": defn.description,
            "placeholders": defn.placeholders,
            "group": defn.group,
            "template": overrides.get(key, defn.default),
            "default_template": defn.default,
            "is_default": is_default,
        })
    return result
