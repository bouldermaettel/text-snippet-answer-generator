"""One-off script to convert flat snippets JSON to grouped format."""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


RUNTIME_META_KEYS = {
    "has_generated_translations", "available_languages",
    "is_generated_translation", "translation_source",
    "language", "linked_snippets", "example_questions",
    "parent_title",
}


def extract_base_title(title: str) -> str:
    """Strip language suffix like '-de', '-en', ' [EN]', etc."""
    # Auto-generated translations: "some-title-de [EN]"
    m = re.match(r'^(.+?)\s*\[(?:DE|EN|FR|IT)\]$', title, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return title


def strip_lang_suffix(title: str) -> str:
    """Strip trailing -de, -en, -fr, -it from title."""
    for lang in ["de", "en", "fr", "it", "es", "pt", "nl", "pl", "ru", "zh", "ja", "ko"]:
        if title.lower().endswith(f"-{lang}"):
            return title[: -len(lang) - 1]
    return title


def convert(flat_entries: list[dict]) -> list[dict]:
    # Phase 1: build a map of title -> entry for quick lookup
    by_title: dict[str, dict] = {}
    for entry in flat_entries:
        by_title[entry["title"]] = entry

    # Phase 2: group entries by their logical base title
    # linked_snippets tells us which entries belong together
    # Auto-translations have is_generated_translation + parent_title
    groups: dict[str, list[dict]] = defaultdict(list)
    assigned: set[str] = set()

    for entry in flat_entries:
        title = entry["title"]
        if title in assigned:
            continue

        meta = entry.get("metadata") or {}
        is_gen = meta.get("is_generated_translation", False)

        if is_gen:
            # Auto-generated translation - will be grouped with parent
            parent_title = meta.get("parent_title", "")
            if parent_title:
                base = strip_lang_suffix(parent_title)
                groups[base].append(entry)
                assigned.add(title)
            continue

        linked = meta.get("linked_snippets", [])
        base = strip_lang_suffix(title)

        groups[base].append(entry)
        assigned.add(title)

        for linked_title in linked:
            if linked_title in assigned:
                continue
            if linked_title in by_title:
                groups[base].append(by_title[linked_title])
                assigned.add(linked_title)

    # Also pick up auto-translations that weren't assigned yet
    for entry in flat_entries:
        title = entry["title"]
        if title in assigned:
            continue
        meta = entry.get("metadata") or {}
        is_gen = meta.get("is_generated_translation", False)
        if is_gen:
            parent_title = meta.get("parent_title", "")
            base = strip_lang_suffix(parent_title) if parent_title else strip_lang_suffix(extract_base_title(title))
            groups[base].append(entry)
            assigned.add(title)
        else:
            base = strip_lang_suffix(title)
            groups[base].append(entry)
            assigned.add(title)

    # Phase 3: build grouped output
    output: list[dict] = []
    for base_title, entries in groups.items():
        # Find the primary entry (non-translation, preferably de)
        originals = [e for e in entries if not (e.get("metadata") or {}).get("is_generated_translation")]
        generated = [e for e in entries if (e.get("metadata") or {}).get("is_generated_translation")]

        if not originals and not generated:
            continue

        primary = originals[0] if originals else generated[0]
        primary_meta = primary.get("metadata") or {}

        # Build shared metadata
        shared_meta: dict = {}
        for key in ["category", "heading", "instructions", "prerequisites"]:
            val = primary_meta.get(key)
            if val:
                shared_meta[key] = val

        # Build translations
        translations: dict[str, dict] = {}
        for entry in originals:
            meta = entry.get("metadata") or {}
            lang = meta.get("language", "")
            if not lang:
                continue
            tr: dict = {"text": entry["text"]}
            eq = meta.get("example_questions", [])
            if eq:
                tr["example_questions"] = eq
            translations[lang] = tr

        for entry in generated:
            meta = entry.get("metadata") or {}
            lang = meta.get("language", "")
            if not lang:
                continue
            tr: dict = {
                "text": entry["text"],
                "is_generated_translation": True,
            }
            eq = meta.get("example_questions", [])
            if eq:
                tr["example_questions"] = eq
            translations[lang] = tr

        grouped_entry: dict = {
            "title": base_title,
            "group": primary.get("group", ""),
        }
        if shared_meta:
            grouped_entry["metadata"] = shared_meta
        grouped_entry["translations"] = translations

        output.append(grouped_entry)

    return output


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python convert_flat_to_grouped.py <input.json> [output.json]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.with_stem(input_path.stem + "_grouped")

    with open(input_path, encoding="utf-8") as f:
        flat_entries = json.load(f)

    grouped = convert(flat_entries)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(grouped, f, ensure_ascii=False, indent=2)

    print(f"Converted {len(flat_entries)} flat entries -> {len(grouped)} grouped entries")
    print(f"Written to: {output_path}")


if __name__ == "__main__":
    main()
