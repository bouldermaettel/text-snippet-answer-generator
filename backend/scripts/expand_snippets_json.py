#!/usr/bin/env python3
"""Expand snippets_clean.json with auto-generated translations from DB and LLM example questions.

Produces a **flat** JSON array where every snippet (original and auto-generated
translation) is its own top-level entry.  Auto-generated translations are marked
with ``metadata.is_generated_translation = true`` and ``metadata.parent_title``.

Steps:
1. Read current snippets_clean.json
2. Query the running backend API for all snippets + auto-translations
3. Flatten auto-translations into top-level entries
4. Generate example questions in German for each heading group via LLM
5. Translate those questions to EN/FR/IT
6. Assign questions to all entries
7. Write the expanded file

Usage:
    python expand_snippets_json.py [--input FILE] [--output FILE] [--dry-run]

Requires: the backend to be running at localhost:8000 with data loaded.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from openai import AzureOpenAI

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BACKEND_URL = "http://localhost:8000"
TARGET_LANGUAGES = ["en", "fr", "it"]


def get_auth_token(email: str, password: str) -> str:
    r = requests.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"email": email, "password": password},
    )
    r.raise_for_status()
    return r.json()["access_token"]


def fetch_all_snippets(token: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(
        f"{BACKEND_URL}/api/snippets",
        params={"limit": 500, "offset": 0, "include_translations": "true"},
        headers=headers,
    )
    r.raise_for_status()
    return r.json()["snippets"]


def build_translation_map(
    db_snippets: list[dict],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Build a map: parent_title -> {lang: {text, ...}} for auto-generated translations."""
    translations = [
        s
        for s in db_snippets
        if s.get("metadata", {}).get("is_generated_translation")
    ]

    title_to_translations: dict[str, dict[str, dict[str, Any]]] = {}
    for t in translations:
        meta = t.get("metadata", {})
        lang = meta.get("language", "")
        title_with_suffix = t["title"]
        parent_title = title_with_suffix.rsplit(" [", 1)[0] if " [" in title_with_suffix else title_with_suffix
        if parent_title and lang:
            title_to_translations.setdefault(parent_title, {})[lang] = {
                "text": t["text"],
                "metadata": meta,
            }

    return title_to_translations


def get_llm_client() -> AzureOpenAI:
    from dotenv import load_dotenv

    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)

    return AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    )


def generate_example_questions_de(
    client: AzureOpenAI, deployment: str, heading: str, text_de: str
) -> list[str]:
    """Generate 1-2 example questions in German that a customer might ask."""
    prompt = (
        "Du bist ein Kundensupport-Assistent bei Swissmedic. "
        "Basierend auf dem folgenden Antworttext, generiere genau 2 kurze Fragen auf Deutsch, "
        "die ein Kunde stellen könnte, auf die dieser Text die Antwort wäre.\n\n"
        "Regeln:\n"
        "- Die Fragen sollen aus Kundensicht formuliert sein\n"
        "- Kurz und natürlich (wie ein Kunde fragen würde)\n"
        "- Gib NUR die 2 Fragen zurück, eine pro Zeile, ohne Nummerierung oder Aufzählungszeichen\n\n"
        f"Thema: {heading}\n\n"
        f"Antworttext:\n{text_de[:1500]}"
    )

    try:
        r = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        if r.choices and r.choices[0].message.content:
            raw = r.choices[0].message.content.strip()
            questions = [q.strip() for q in raw.split("\n") if q.strip()]
            # Remove numbering if present
            cleaned = []
            for q in questions[:2]:
                q = q.lstrip("0123456789.-) ").strip()
                if q:
                    cleaned.append(q)
            return cleaned
    except Exception as e:
        logger.warning("Failed to generate questions for '%s': %s", heading, e)
    return []


def translate_questions(
    client: AzureOpenAI,
    deployment: str,
    questions_de: list[str],
    target_langs: list[str],
) -> dict[str, list[str]]:
    """Translate German questions to multiple target languages in one call."""
    if not questions_de:
        return {lang: [] for lang in target_langs}

    lang_names = {"en": "English", "fr": "French", "it": "Italian"}
    questions_text = "\n".join(f"- {q}" for q in questions_de)

    prompt = (
        "Translate the following German customer support questions to English, French, and Italian. "
        "Keep the same meaning and natural tone.\n\n"
        "Output format: for each language, output the language code on its own line, "
        "followed by the translated questions (one per line, prefixed with '- '). Example:\n"
        "en\n- English question 1\n- English question 2\n"
        "fr\n- French question 1\n- French question 2\n"
        "it\n- Italian question 1\n- Italian question 2\n\n"
        f"German questions:\n{questions_text}"
    )

    try:
        r = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3,
        )
        if r.choices and r.choices[0].message.content:
            raw = r.choices[0].message.content.strip()
            return _parse_translated_questions(raw, target_langs)
    except Exception as e:
        logger.warning("Failed to translate questions: %s", e)

    return {lang: [] for lang in target_langs}


def _parse_translated_questions(raw: str, target_langs: list[str]) -> dict[str, list[str]]:
    """Parse LLM output with language-grouped translated questions."""
    result: dict[str, list[str]] = {lang: [] for lang in target_langs}
    current_lang = None

    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        low = line.lower().rstrip(":")
        if low in target_langs:
            current_lang = low
            continue
        if current_lang and line.startswith("- "):
            q = line[2:].strip()
            if q:
                result[current_lang].append(q)
        elif current_lang and line.startswith("-"):
            q = line[1:].strip()
            if q:
                result[current_lang].append(q)

    return result


def group_snippets_by_heading(
    snippets: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group snippets by (category, heading) key. Returns {key: [snippets]}."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for s in snippets:
        meta = s.get("metadata", {})
        key = f"{meta.get('category', '')}|{meta.get('heading', '')}"
        groups.setdefault(key, []).append(s)
    return groups


def expand_snippets(
    snippets: list[dict[str, Any]],
    translation_map: dict[str, dict[str, dict[str, Any]]],
    client: AzureOpenAI,
    deployment: str,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Expand into a flat list: originals + auto-translations as top-level entries."""

    # Remove any leftover nested 'translations' field from prior runs
    for s in snippets:
        s.pop("translations", None)

    # Step 1: Generate and distribute example questions by heading group
    heading_groups = group_snippets_by_heading(snippets)
    total_groups = len(heading_groups)
    logger.info("Processing %d heading groups for example questions", total_groups)

    questions_by_heading: dict[str, dict[str, list[str]]] = {}

    for idx, (key, group_snippets) in enumerate(heading_groups.items()):
        category, heading = key.split("|", 1) if "|" in key else ("", key)
        if not heading:
            heading = "(no heading)"

        de_snippet = None
        for s in group_snippets:
            lang = s.get("metadata", {}).get("language", "")
            if lang == "de":
                de_snippet = s
                break
        if not de_snippet:
            de_snippet = group_snippets[0]

        de_text = de_snippet["text"]
        logger.info("[%d/%d] Generating questions for: %s", idx + 1, total_groups, heading)

        if dry_run:
            questions_de = [f"[Beispielfrage 1 für {heading}]", f"[Beispielfrage 2 für {heading}]"]
            translated = {
                lang: [f"[Example Q1 for {heading} in {lang}]", f"[Example Q2 for {heading} in {lang}]"]
                for lang in TARGET_LANGUAGES
            }
        else:
            questions_de = generate_example_questions_de(client, deployment, heading, de_text)
            if not questions_de:
                logger.warning("No questions generated for '%s', skipping", heading)
                continue
            time.sleep(0.5)
            translated = translate_questions(client, deployment, questions_de, TARGET_LANGUAGES)
            time.sleep(0.5)

        all_qs: dict[str, list[str]] = {"de": questions_de}
        all_qs.update(translated)
        questions_by_heading[key] = all_qs

        for s in group_snippets:
            lang = s.get("metadata", {}).get("language", "")
            s["metadata"]["example_questions"] = all_qs.get(lang, questions_de)

    # Step 2: Flatten auto-generated translations into top-level entries
    output: list[dict[str, Any]] = list(snippets)

    for s in snippets:
        title = s["title"]
        tr_langs = translation_map.get(title, {})
        if not tr_langs:
            continue
        group = s.get("group", "")
        parent_meta = s.get("metadata", {})
        heading_key = f"{parent_meta.get('category', '')}|{parent_meta.get('heading', '')}"
        heading_qs = questions_by_heading.get(heading_key, {})

        for lang, tr_data in tr_langs.items():
            tr_meta: dict[str, Any] = {
                "category": parent_meta.get("category", ""),
                "heading": parent_meta.get("heading", ""),
                "language": lang,
                "is_generated_translation": True,
                "parent_title": title,
                "example_questions": heading_qs.get(lang, heading_qs.get("de", [])),
            }
            if parent_meta.get("instructions"):
                tr_meta["instructions"] = parent_meta["instructions"]
            if parent_meta.get("prerequisites"):
                tr_meta["prerequisites"] = parent_meta["prerequisites"]

            output.append({
                "text": tr_data["text"],
                "title": f"{title} [{lang.upper()}]",
                "group": group,
                "metadata": tr_meta,
            })

    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Expand snippets_clean.json with translations + example questions")
    parser.add_argument(
        "--input", "-i",
        default="../../test-data/antwortvorlagen-actors/snippets_clean.json",
    )
    parser.add_argument(
        "--output", "-o",
        default="../../test-data/antwortvorlagen-actors/snippets_clean.json",
    )
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM calls, use placeholder questions")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    input_path = (script_dir / args.input).resolve()
    output_path = (script_dir / args.output).resolve()

    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        return 1

    # Load .env for credentials
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    admin_email = os.environ.get("ADMIN_EMAIL", "")
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_email or not admin_password:
        logger.error("ADMIN_EMAIL and ADMIN_PASSWORD must be set in .env")
        return 1

    # Step 1: Read current JSON (strip any existing auto-translations so we
    # always work from originals only; translations are re-fetched from the DB)
    logger.info("Reading: %s", input_path)
    with open(input_path, encoding="utf-8") as f:
        all_entries: list[dict[str, Any]] = json.load(f)
    snippets = [s for s in all_entries if not (s.get("metadata") or {}).get("is_generated_translation")]
    n_skipped = len(all_entries) - len(snippets)
    logger.info("Loaded %d originals from JSON (skipped %d auto-translations)", len(snippets), n_skipped)

    # Step 2: Fetch DB data
    logger.info("Fetching snippets from backend API...")
    try:
        token = get_auth_token(admin_email, admin_password)
        db_snippets = fetch_all_snippets(token)
        logger.info("Fetched %d entries from DB (originals + translations)", len(db_snippets))
    except Exception as e:
        logger.error("Failed to fetch from backend: %s", e)
        logger.info("Is the backend running at %s?", BACKEND_URL)
        return 1

    # Step 3: Build translation map
    translation_map = build_translation_map(db_snippets)
    n_parents_with_tr = len(translation_map)
    n_translations = sum(len(v) for v in translation_map.values())
    logger.info("Found %d parents with %d auto-generated translations", n_parents_with_tr, n_translations)

    # Step 4: Set up LLM client
    deployment = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4-32k")
    if args.dry_run:
        client = None  # type: ignore
        logger.info("DRY RUN: skipping LLM calls")
    else:
        client = get_llm_client()
        logger.info("Using Azure OpenAI deployment: %s", deployment)

    # Step 5: Expand
    expanded = expand_snippets(snippets, translation_map, client, deployment, dry_run=args.dry_run)

    # Stats
    n_originals = sum(1 for s in expanded if not s.get("metadata", {}).get("is_generated_translation"))
    n_auto_tr = sum(1 for s in expanded if s.get("metadata", {}).get("is_generated_translation"))
    with_questions = sum(1 for s in expanded if s.get("metadata", {}).get("example_questions"))
    logger.info("Results: %d total (%d originals + %d auto-translations), %d with example_questions",
                len(expanded), n_originals, n_auto_tr, with_questions)

    # Step 6: Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(expanded, f, ensure_ascii=False, indent=2)
    logger.info("Written to: %s", output_path)

    return 0


if __name__ == "__main__":
    exit(main())
