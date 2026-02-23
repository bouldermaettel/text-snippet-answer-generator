#!/usr/bin/env python3
"""
Clean and anonymize extracted snippets for use as test/seed data.

Processes extracted_snippets.json by:
1. Removing non-template entries (internal notes, file refs, email threads)
2. Cleaning noise artifacts (garbage chars, separators, internal instructions)
3. Fixing broken URLs (concatenated URL+text)
4. Applying deterministic PII anonymization (names, emails, phones, IDs, addresses)
5. Keeping all URLs intact (per anonymize.py rules)
6. Recomputing linked_snippets after removals

Usage:
    python clean_snippets.py [--input FILE] [--output FILE]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


TITLES_TO_REMOVE = {
    "aa-verfugungen-de",
    "unkooperative-firmen-de",
    "keine-webseite-vorhanden-de",
    "arbeitsanweisung-swissdamed-de",
    "datenschutz-wettbewerbsrechtliches-de",
    "user-onboarding-status-onboarding-de",
}

PII_REPLACEMENTS: list[tuple[str, str]] = [
    # Emails (before names, so names inside emails don't get partial matches)
    ("susanne.wydenkeller@swissmedic.ch", "[EMAIL]"),
    ("Simon.Lory@swissmedic.ch", "[EMAIL]"),

    # Phone numbers
    ("+41 58 464 60 49", "[PHONE]"),
    ("Tel. [PHONE]", "[PHONE]"),

    # Specific IDs (longer/more specific first)
    ("INC000014535090", "[ID_NUMBER]"),
    ("CHE-486.754.425", "[ID_NUMBER]"),
    ("CHE-106.541.045", "[ID_NUMBER]"),
    ("CHE-114.644.629", "[ID_NUMBER]"),
    ("CHE-348.695.028", "[ID_NUMBER]"),
    ("CH-348.695.028", "[ID_NUMBER]"),
    ("CHE123456789", "[ID_NUMBER]"),
    ("CHRN-MF-20000589", "[ID_NUMBER]"),
    ("CHRN-AR-20003934", "[ID_NUMBER]"),
    ("CHRN-AR-xxxxx", "[ID_NUMBER]"),

    # Specific addresses (not Swissmedic HQ)
    ("Breitfeldstrasse 12, 9015 St. Gallen", "[ADDRESS]"),
    ("Hühnerhubelstrasse 59, 3123 Belp", "[ADDRESS]"),

    # Company names (specific, not generic template vars)
    ("AB MEDICA Sagl", "[COMPANY]"),
    ("MedEnvoy", "[COMPANY]"),
    ("NMT", "[COMPANY]"),

    # Person names (longer/multi-word first to avoid partial matches)
    ("Susanne Wydenkeller Hinder", "[NAME]"),
    ("Wydenkeller Hinder Susanne", "[NAME]"),
    ("Ron Robsona", "[NAME]"),
    ("Ron Robsonle", "[NAME]"),
    ("Ron Robson", "[NAME]"),
    ("Simon Lory", "[NAME]"),
    ("Herr Seiler", "[NAME]"),
    ("Lorenzo", "[NAME]"),
    ("Susanne", "[NAME]"),
    ("Vince", "[NAME]"),
]

SEPARATOR_PATTERN = re.compile(r"^\*{10,}$", re.MULTILINE)
GARBAGE_PATTERN = re.compile(r"\nl,\s+,{5,}$")
DASH_SEPARATOR_PATTERN = re.compile(r"\n---\s*$")
FILE_PATH_PATTERN = re.compile(
    r"^(Excelliste:\s+)?M:\\[^\n]+$", re.MULTILINE
)
BROKEN_URL_PATTERN = re.compile(
    r"(\.html)(swissdamed:\s)", re.IGNORECASE
)


def clean_text(
    text: str, title: str
) -> dict[str, str | None]:
    """Apply all text cleanup transformations and extract metadata sections.

    Returns dict with keys: text, instructions, prerequisites.
    """
    text, instructions, prerequisites = _extract_metadata_sections(text, title)
    text = _remove_noise(text)
    text = _fix_broken_urls(text)
    text = _anonymize(text)
    text = _normalize_whitespace(text)
    if instructions:
        instructions = _anonymize(instructions.strip())
    if prerequisites:
        prerequisites = _anonymize(prerequisites.strip())
    return {
        "text": text,
        "instructions": instructions,
        "prerequisites": prerequisites,
    }


def _extract_metadata_sections(
    text: str, title: str
) -> tuple[str, str | None, str | None]:
    """Split text into (customer_text, instructions, prerequisites).

    Extracts internal process steps into ``instructions`` and triggering
    question/context into ``prerequisites``, keeping only the clean
    customer-facing template in the returned text.
    """
    instructions: str | None = None
    prerequisites: str | None = None

    if title == "schreibregelung-verfugung-de":
        marker = "Sehr geehrte"
        idx = text.find(marker)
        if idx > 0:
            instructions = text[:idx].strip()
            text = text[idx:].strip()

    elif title == "sprachregelung-verfugung-de":
        sep_idx = text.find("*" * 10)
        if sep_idx != -1:
            after = text[sep_idx:]
            after = re.sub(r"^\*+", "", after).strip()
            instructions = after
            text = text[:sep_idx].strip()

    elif title == "registrierung-nach-verfugung-de":
        marker = "Email Text zur Bestätigung der Registrierung:"
        if text.startswith(marker):
            instructions = marker
            text = text[len(marker) :].strip()

    elif title == "registrierung-nach-verfugung-it":
        marker = "Textvorlage für die zweite Verfügung"
        idx = text.find(marker)
        if idx != -1:
            instructions = text[idx:].strip()
            text = text[:idx].strip()

    elif title == "reaktivierung-nach-verfugungsabschluss-de":
        sep_idx = text.find("*" * 10)
        if sep_idx != -1:
            instructions = text[:sep_idx].strip()
            after_sep = text[sep_idx:]
            after_sep = re.sub(r"^\*+", "", after_sep).strip()
            marker = "Standardtext:\n"
            m_idx = after_sep.find(marker)
            if m_idx != -1:
                text = after_sep[m_idx + len(marker) :].strip()
            else:
                text = after_sep
        else:
            marker = "Standardtext:\n"
            m_idx = text.find(marker)
            if m_idx != -1:
                instructions = text[:m_idx].strip()
                text = text[m_idx + len(marker) :].strip()

    elif title == "verifizierung-neuer-company-admin-de":
        ref_pattern = re.compile(r"\s*\(s\.\s*AA\s+Kapitel\s+\d+\)")
        match = ref_pattern.search(text)
        if match:
            instructions = match.group(0).strip()
            text = text[: match.start()] + text[match.end() :]
            text = text.strip()

    elif title == "vorgehen-firma-meldet-firma-ohne-chrn-de":
        marker = "Das Ticket wie folgt beantworten:\n"
        idx = text.find(marker)
        if idx != -1:
            instructions = text[:idx].strip()
            text = text[idx + len(marker) :].strip()

    elif title == "ch-login-bestehender-account-de":
        context_end = "kann man folgendes antworten:\n"
        ctx_idx = text.find(context_end)
        if ctx_idx != -1:
            prerequisites = text[: ctx_idx + len(context_end)].strip()
            text = text[ctx_idx + len(context_end) :].strip()
        paren_pattern = re.compile(
            r"\s*\(Falls es detaillierte Informationen[^)]+\)\s*"
        )
        match = paren_pattern.search(text)
        if match:
            instructions = match.group(0).strip()
            text = text[: match.start()] + text[match.end() :]
            text = text.strip()

    elif title == "passwortwechsel-anleitungen-eiam-de":
        internal = "Falls dies nicht funktioniert, müssen wir beim BIT eine Reset des Accounts beantragen."
        if internal in text:
            instructions = internal
            text = text.replace(internal + "\n", "").replace(internal, "")
            text = text.strip()

    elif title == "open-data-liste-fr":
        for sep in ("-----\n", "-----"):
            idx = text.find(sep)
            if idx != -1:
                before = text[:idx].strip()
                after = text[idx + len(sep) :].strip()
                german_marker = "User haben Mails"
                if after.startswith(german_marker):
                    instructions = after
                    french_parts = []
                    for part in [before]:
                        french_parts.append(part)
                    remaining = ""
                    final_marker = "L'office de la statistique"
                    fi = after.find(final_marker)
                    if fi != -1:
                        remaining = after[fi:].strip()
                    text = before + ("\n" + remaining if remaining else "")
                    text = text.strip()
                break

    elif title == "zwei-faktor-validierung-de":
        instructions = text
        text = (
            "Bei Problemen mit der Zwei-Faktor-Authentifizierung (SMS wird nicht empfangen): "
            "Prüfen Sie, ob die richtige Telefonnummer hinterlegt ist. "
            "Über die Sicherheitsfragen können Sie eine neue Mobile-Nummer eingeben "
            "und erhalten dann einen Bestätigungscode via SMS."
        )

    elif title == "chrn-inaktivieren-de":
        example1_end = "Beispiel\nVielen Dank"
        idx = text.find(example1_end)
        if idx != -1:
            instructions = text[: idx + len("Beispiel")].strip()
            text = text[idx + len("Beispiel\n") :].strip()

    # --- Prerequisites: Frage/Antwort pattern ---
    elif title == "rolle-wirtschaftsakteur-de":
        marker = "Besten Dank für Ihre Anfrage."
        idx = text.find(marker)
        if idx > 0:
            prerequisites = text[:idx].strip()
            text = text[idx:].strip()

    elif title in (
        "ch-rep-ubergangsregelung-de",
        "chrn-falsch-verknupft-de",
        "anfrage-bestatigung-mandate-de",
        "mandat-typ-welchen-de",
    ):
        for answer_marker in ("Antwort:\n", "Antwort:\r\n"):
            idx = text.find(answer_marker)
            if idx != -1:
                prerequisites = text[:idx].strip()
                text = text[idx + len(answer_marker) :].strip()
                break

    elif title == "chrn-automatisch-inaktiviert-de":
        for sep in ("-------\n", "-------"):
            idx = text.find(sep)
            if idx != -1:
                prerequisites = text[:idx].strip()
                text = text[idx + len(sep) :].strip()
                break

    return text, instructions, prerequisites


def _remove_noise(text: str) -> str:
    """Remove garbage characters, separators, and file paths."""
    text = GARBAGE_PATTERN.sub("", text)
    text = SEPARATOR_PATTERN.sub("", text)
    text = DASH_SEPARATOR_PATTERN.sub("", text)
    text = FILE_PATH_PATTERN.sub("", text)

    cleaned_lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("-->"):
            continue
        if stripped.startswith("Letzte Änderung:") and "Seite" in stripped:
            continue
        cleaned_lines.append(line)
    text = "\n".join(cleaned_lines)

    return text


def _fix_broken_urls(text: str) -> str:
    """Fix URLs concatenated with following text (no space/newline between)."""
    text = BROKEN_URL_PATTERN.sub(r"\1\n\2", text)
    return text


def _anonymize(text: str) -> str:
    """Apply deterministic PII replacements."""
    for original, placeholder in PII_REPLACEMENTS:
        text = text.replace(original, placeholder)
    return text


def _normalize_whitespace(text: str) -> str:
    """Clean up excessive blank lines while preserving paragraph structure."""
    lines = text.split("\n")
    result: list[str] = []
    prev_empty = False
    for line in lines:
        is_empty = not line.strip()
        if is_empty and prev_empty:
            continue
        result.append(line)
        prev_empty = is_empty

    text = "\n".join(result).strip()
    return text


def recompute_linked_snippets(
    snippets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Recompute linked_snippets based on remaining titles after filtering."""
    remaining_titles = {s["title"] for s in snippets}

    heading_groups: dict[str, list[dict[str, Any]]] = {}
    for snippet in snippets:
        meta = snippet.get("metadata", {})
        key = f"{meta.get('category', '')}|{meta.get('heading', '')}"
        heading_groups.setdefault(key, []).append(snippet)

    for group_snippets in heading_groups.values():
        if len(group_snippets) > 1:
            titles = [s["title"] for s in group_snippets]
            for snippet in group_snippets:
                other_titles = [
                    t
                    for t in titles
                    if t != snippet["title"] and t in remaining_titles
                ]
                if other_titles:
                    snippet["metadata"]["linked_snippets"] = other_titles
                elif "linked_snippets" in snippet.get("metadata", {}):
                    del snippet["metadata"]["linked_snippets"]
        else:
            snippet = group_snippets[0]
            if "linked_snippets" in snippet.get("metadata", {}):
                del snippet["metadata"]["linked_snippets"]

    return snippets


def process_snippets(snippets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Full pipeline: filter, clean, anonymize, recompute links."""
    filtered = [s for s in snippets if s["title"] not in TITLES_TO_REMOVE]

    for snippet in filtered:
        result = clean_text(snippet["text"], snippet["title"])
        snippet["text"] = result["text"]
        if result["instructions"]:
            snippet["metadata"]["instructions"] = result["instructions"]
        if result["prerequisites"]:
            snippet["metadata"]["prerequisites"] = result["prerequisites"]

    filtered = [s for s in filtered if len(s["text"].strip()) >= 20]

    filtered = recompute_linked_snippets(filtered)

    return filtered


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean and anonymize extracted snippets"
    )
    parser.add_argument(
        "--input",
        "-i",
        default="../../test-data/antwortvorlagen-actors/extracted_snippets.json",
        help="Path to input JSON file",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="../../test-data/antwortvorlagen-actors/snippets_clean.json",
        help="Path to output JSON file",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    input_path = (script_dir / args.input).resolve()
    output_path = (script_dir / args.output).resolve()

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1

    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")

    with open(input_path, encoding="utf-8") as f:
        snippets: list[dict[str, Any]] = json.load(f)

    print(f"Loaded {len(snippets)} raw snippets")

    cleaned = process_snippets(snippets)

    removed = len(snippets) - len(cleaned)
    print(f"Removed {removed} non-template/empty snippets")
    print(f"Output: {len(cleaned)} cleaned snippets")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    lang_counts: dict[str, int] = {}
    for s in cleaned:
        lang = s.get("metadata", {}).get("language", "unknown")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

    print("\nBy language:")
    for lang, count in sorted(lang_counts.items()):
        print(f"  {lang}: {count}")

    headings = {s.get("metadata", {}).get("heading", "") for s in cleaned}
    print(f"\nUnique headings: {len(headings)}")

    with_instr = sum(
        1 for s in cleaned if s.get("metadata", {}).get("instructions")
    )
    with_prereq = sum(
        1 for s in cleaned if s.get("metadata", {}).get("prerequisites")
    )
    print(f"With instructions: {with_instr}")
    print(f"With prerequisites: {with_prereq}")

    print(f"\nJSON written to: {output_path}")
    return 0


if __name__ == "__main__":
    exit(main())
