#!/usr/bin/env python3
"""Migration script to add translations for missing language variants.

This script groups snippets by their base title, identifies which languages
are missing in each group, and creates new translated snippets to fill the gaps.
It uses the German version as the primary source when available.

Usage:
    cd backend
    python -m scripts.translate_existing [--dry-run] [--limit N]

Options:
    --dry-run       Show what would be done without making changes
    --limit N       Only process first N groups (for testing)
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings, get_settings
from app.store import add_snippets, list_snippets
from app.translation import is_translation_enabled, translate_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Target languages
TARGET_LANGUAGES = {"de", "en", "fr", "it"}


def group_snippets_by_base(snippets: list[dict]) -> dict[str, list[dict]]:
    """Group snippets by base title (without language suffix).
    
    For example, 'company-user-einladen-de' and 'company-user-einladen-en'
    would be grouped together under 'company-user-einladen'.
    """
    by_base = defaultdict(list)
    for s in snippets:
        title = s.get("title", "") or ""
        base = title
        for suffix in ["-de", "-en", "-fr", "-it"]:
            if title.endswith(suffix):
                base = title[:-3]
                break
        by_base[base].append(s)
    return dict(by_base)


def get_snippet_language(snippet: dict) -> str:
    """Get the language of a snippet from metadata or title suffix."""
    metadata = snippet.get("metadata") or {}
    lang = metadata.get("language", "")
    if lang:
        return lang.lower()
    
    # Fall back to title suffix
    title = snippet.get("title", "") or ""
    for suffix in ["-de", "-en", "-fr", "-it"]:
        if title.endswith(suffix):
            return suffix[1:]  # Remove the dash
    
    return ""


def find_source_snippet(group: list[dict]) -> dict | None:
    """Find the best source snippet for translation (prefer German).
    
    Returns the German version if available, otherwise the first available.
    """
    # First, try to find German version
    for s in group:
        lang = get_snippet_language(s)
        if lang == "de":
            return s
    
    # Fall back to first snippet with a known language
    for s in group:
        lang = get_snippet_language(s)
        if lang in TARGET_LANGUAGES:
            return s
    
    # Last resort: return first snippet
    return group[0] if group else None


def get_existing_languages(group: list[dict]) -> set[str]:
    """Get the set of languages that already exist in a group."""
    existing = set()
    for s in group:
        lang = get_snippet_language(s)
        if lang:
            existing.add(lang)
    return existing


def translate_example_questions(
    questions: list[str],
    source_lang: str,
    target_lang: str,
    settings: Settings,
) -> list[str]:
    """Translate a list of example questions from source to target language."""
    translated = []
    for q in questions:
        if q and q.strip():
            t = translate_text(q.strip(), source_lang, target_lang, settings)
            if t:
                translated.append(t)
    return translated


def create_translated_snippet(
    source_snippet: dict,
    source_lang: str,
    target_lang: str,
    base_title: str,
    settings: Settings,
    dry_run: bool = False,
) -> bool:
    """Create a new snippet as a translation of the source.
    
    Args:
        source_snippet: The source snippet to translate from
        source_lang: Source language code
        target_lang: Target language code
        base_title: Base title without language suffix
        settings: Application settings
        dry_run: If True, don't actually create the snippet
    
    Returns True if successful, False on error.
    """
    text = source_snippet.get("text", "")
    if not text.strip():
        logger.warning("Source snippet has no text, skipping")
        return False
    
    # Translate the main text
    translated_text = translate_text(text, source_lang, target_lang, settings)
    if not translated_text:
        logger.error("Failed to translate text from %s to %s", source_lang, target_lang)
        return False
    
    # Prepare metadata
    source_metadata = source_snippet.get("metadata") or {}
    new_metadata = {
        "language": target_lang,
    }
    
    # Copy relevant metadata fields
    for key in ["linked_snippets"]:
        if key in source_metadata:
            new_metadata[key] = source_metadata[key]
    
    # Translate example questions if present
    example_questions = source_metadata.get("example_questions", [])
    if example_questions:
        translated_questions = translate_example_questions(
            example_questions, source_lang, target_lang, settings
        )
        if translated_questions:
            new_metadata["example_questions"] = translated_questions
            logger.info(
                "  Translated %d example questions for %s",
                len(translated_questions),
                target_lang,
            )
    
    # Create new title with language suffix
    new_title = f"{base_title}-{target_lang}"
    
    # Get group from source
    group = source_snippet.get("group", "")
    
    if dry_run:
        logger.info(
            "  [DRY RUN] Would create snippet '%s' (translated from %s to %s)",
            new_title,
            source_lang,
            target_lang,
        )
        if example_questions:
            logger.info("    Would translate %d example questions", len(example_questions))
        return True
    
    try:
        # Use add_snippets with skip_translation=True to avoid recursive translation
        result = add_snippets(
            items=[{
                "text": translated_text,
                "title": new_title,
                "group": group,
                "metadata": new_metadata,
            }],
            skip_translation=True,  # Don't generate more translations
        )
        logger.info("  Created snippet '%s' (%s)", new_title, target_lang)
        return bool(result)
    except Exception as e:
        logger.error("  Failed to create snippet '%s': %s", new_title, e)
        return False


def process_group(
    base_title: str,
    group: list[dict],
    settings: Settings,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Process a single logical group and create missing translations.
    
    Args:
        base_title: Base title of the group
        group: List of snippets in this group
        settings: Application settings
        dry_run: If True, don't actually make changes
    
    Returns (created_count, error_count).
    """
    # Find existing languages
    existing = get_existing_languages(group)
    missing = TARGET_LANGUAGES - existing
    
    if not missing:
        logger.debug("Group '%s' has all languages, skipping", base_title)
        return 0, 0
    
    # Find source snippet (prefer German)
    source = find_source_snippet(group)
    if not source:
        logger.warning("Group '%s' has no valid source snippet", base_title)
        return 0, 1
    
    source_lang = get_snippet_language(source)
    if not source_lang:
        logger.warning("Could not determine language for source snippet in group '%s'", base_title)
        return 0, 1
    
    logger.info(
        "Group '%s': existing=%s, missing=%s, source=%s",
        base_title[:40],
        sorted(existing),
        sorted(missing),
        source_lang,
    )
    
    created = 0
    errors = 0
    
    for target_lang in sorted(missing):
        if create_translated_snippet(
            source, source_lang, target_lang, base_title, settings, dry_run
        ):
            created += 1
        else:
            errors += 1
    
    return created, errors


def main():
    parser = argparse.ArgumentParser(
        description="Create translated snippets to fill language gaps in snippet groups"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process first N groups (for testing)",
    )
    args = parser.parse_args()

    settings = get_settings()
    
    # Check if translation is enabled
    if not settings.enable_translation_indexing:
        logger.error(
            "Translation indexing is disabled. Set ENABLE_TRANSLATION_INDEXING=true in .env"
        )
        sys.exit(1)
    
    if not is_translation_enabled(settings):
        logger.error(
            "No LLM provider available for translation. Configure Azure OpenAI or Ollama."
        )
        sys.exit(1)
    
    logger.info("Target languages: %s", sorted(TARGET_LANGUAGES))
    
    if args.dry_run:
        logger.info("DRY RUN MODE - no changes will be made")
    
    # Load all snippets
    logger.info("Fetching all snippets...")
    all_snippets = []
    offset = 0
    batch_size = 500
    
    while True:
        snippets, total = list_snippets(limit=batch_size, offset=offset)
        if not snippets:
            break
        all_snippets.extend(snippets)
        offset += batch_size
        if offset >= total:
            break
    
    logger.info("Loaded %d snippets", len(all_snippets))
    
    # Group by base title
    groups = group_snippets_by_base(all_snippets)
    logger.info("Found %d logical snippet groups", len(groups))
    
    # Calculate totals
    total_missing = 0
    for base, group in groups.items():
        existing = get_existing_languages(group)
        total_missing += len(TARGET_LANGUAGES - existing)
    
    logger.info("Total translations needed: %d", total_missing)
    logger.info("Expected final count: %d snippets", len(all_snippets) + total_missing)
    logger.info("=" * 50)
    
    # Process each group
    groups_processed = 0
    total_created = 0
    total_errors = 0
    groups_skipped = 0
    
    for base_title, group in sorted(groups.items()):
        if args.limit and groups_processed >= args.limit:
            logger.info("Reached limit of %d groups", args.limit)
            break
        
        groups_processed += 1
        
        existing = get_existing_languages(group)
        if existing == TARGET_LANGUAGES:
            groups_skipped += 1
            continue
        
        created, errors = process_group(base_title, group, settings, args.dry_run)
        total_created += created
        total_errors += errors
    
    # Summary
    logger.info("=" * 50)
    logger.info("Migration complete!")
    logger.info("  Groups processed: %d", groups_processed)
    logger.info("  Groups skipped (complete): %d", groups_skipped)
    logger.info("  Translations created: %d", total_created)
    logger.info("  Errors: %d", total_errors)
    
    if args.dry_run:
        logger.info("(DRY RUN - no actual changes were made)")
    else:
        # Show final count
        final_snippets, final_total = list_snippets(limit=1)
        logger.info("Final snippet count: %d", final_total)


if __name__ == "__main__":
    main()
