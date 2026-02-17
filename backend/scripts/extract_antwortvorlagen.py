#!/usr/bin/env python3
"""
Extract snippets from Antwortvorlagen Actors.docx and generate JSON for import.

The document contains multilingual answer templates organized by category and heading.
Each snippet is extracted as a separate language version (DE/FR/IT/EN) with metadata.

Document structure:
- Category (e.g., "Verfügungen") - top-level grouping
- Heading (e.g., "Schreibregelung Verfügung") - the topic, used as title
- Language markers (DE/FR/IT/EN) - indicate language of following content
- Content - the actual text for each language

Usage:
    python extract_antwortvorlagen.py [--input FILE] [--output FILE] [--debug]
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from docx import Document
from docx.text.paragraph import Paragraph


# Language markers used in the document (including English)
LANGUAGE_MARKERS = {"DE", "FR", "IT", "EN"}
# Match language markers at start of line, optionally followed by : or whitespace.
# IMPORTANT: case-sensitive + word boundary to avoid matching "Dear"→DE, "Frage"→FR, "Dell'"→DE, etc.
LANGUAGE_PATTERN = re.compile(r"^(DE|FR|IT|EN)\b\s*[:|\s]?\s*")
# Match standalone language markers (just "DE", "FR", "IT", "EN" as full paragraph)
STANDALONE_LANG_PATTERN = re.compile(r"^(DE|FR|IT|EN)\s*:?\s*$")
# File reference pattern (e.g., <<filename.docx>>)
FILE_REF_PATTERN = re.compile(r"^<<.+>>\s*$")
# Date pattern (e.g., "Montag, 31. März 2025" or "Mittwoch, 26. März 2025")
DATE_PATTERN = re.compile(r"^(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag),\s+\d{1,2}\.\s+\w+\s+\d{4}$", re.IGNORECASE)
# Time pattern (e.g., "15:15" or "08:33")
TIME_PATTERN = re.compile(r"^\d{1,2}:\d{2}$")


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    # Convert to lowercase and replace spaces/special chars with hyphens
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def is_bold_paragraph(paragraph: Paragraph) -> bool:
    """Check if the entire paragraph is bold."""
    if not paragraph.text.strip():
        return False
    for run in paragraph.runs:
        if run.text.strip() and not run.bold:
            return False
    return len(paragraph.runs) > 0


def detect_language(text: str) -> tuple[str | None, str]:
    """
    Detect language marker at the start of text.
    Returns (language_code, remaining_text) or (None, original_text).
    """
    text = text.strip()
    match = LANGUAGE_PATTERN.match(text)
    if match:
        lang = match.group(1).upper()
        remaining = text[match.end():].strip()
        return lang, remaining
    return None, text


def is_standalone_language_marker(text: str) -> str | None:
    """Check if text is just a standalone language marker (e.g., 'DE:', 'EN')."""
    text = text.strip()
    match = STANDALONE_LANG_PATTERN.match(text)
    if match:
        return match.group(1).upper()
    return None


def is_file_reference(text: str) -> bool:
    """Check if text is a file reference like <<filename.docx>>."""
    return bool(FILE_REF_PATTERN.match(text.strip()))


def is_date_or_time(text: str) -> bool:
    """Check if text is a date or time stamp."""
    text = text.strip()
    return bool(DATE_PATTERN.match(text) or TIME_PATTERN.match(text))


def is_metadata_or_noise(text: str) -> bool:
    """Check if text is metadata/noise that should be skipped."""
    text = text.strip()
    # Skip very short lines that are just punctuation or formatting
    if len(text) < 3 and not text.isalpha():
        return True
    return False


def looks_like_heading(text: str, next_para_text: str | None) -> bool:
    """
    Heuristic to detect if a paragraph looks like a heading/topic.
    Headings are typically followed by date stamps.
    """
    text = text.strip()
    # Skip if it's a language marker
    if is_standalone_language_marker(text):
        return False
    # Skip if it's a date/time
    if is_date_or_time(text):
        return False
    # Skip if it's too long (probably content)
    if len(text) > 100:
        return False
    # Skip if it starts with common content patterns
    if text.startswith(("Sehr geehrte", "Dear", "Madame", "Gentil", "Bitte", "Please", "Nous", "Vi ")):
        return False
    # Check if next paragraph is a date (strong indicator of heading)
    if next_para_text and is_date_or_time(next_para_text):
        return True
    return False


def extract_document_structure(doc_path: str, debug: bool = False) -> list[dict[str, Any]]:
    """
    Parse the docx file and extract structured snippets.
    
    Returns a list of snippet dictionaries ready for JSON export.
    """
    doc = Document(doc_path)
    paragraphs = list(doc.paragraphs)
    snippets: list[dict[str, Any]] = []
    
    current_category = "General"
    current_heading = ""  # This is the title for snippets
    current_content: dict[str, list[str]] = {}  # language -> content lines
    current_lang: str | None = None  # Track current active language
    
    def save_current_snippet():
        """Save accumulated content as snippet(s)."""
        nonlocal current_content, current_lang
        
        if not current_heading:
            current_content = {}
            current_lang = None
            return
            
        for lang, lines in current_content.items():
            # Filter out empty lines and join
            filtered_lines = [line for line in lines if line.strip()]
            text = "\n".join(filtered_lines).strip()
            
            # Skip if text is too short or empty
            if not text or len(text) < 20:
                if debug and text:
                    print(f"  -> Skipped too short: {text[:50]}")
                continue
                
            slug = slugify(current_heading)
            # Truncate slug if too long
            if len(slug) > 50:
                slug = slug[:50].rstrip("-")
            title = f"{slug}-{lang.lower()}"
            
            metadata: dict[str, Any] = {
                "category": current_category,
                "heading": current_heading,
                "language": lang.lower(),
            }
            
            snippets.append({
                "text": text,
                "title": title,
                "group": "antwortvorlagen-actors",
                "metadata": metadata,
            })
            
            if debug:
                print(f"  -> Saved snippet: {title} ({len(text)} chars)")
        
        current_content = {}
        current_lang = None
    
    if debug:
        print("Parsing document structure...\n")
    
    i = 0
    while i < len(paragraphs):
        para = paragraphs[i]
        text = para.text.strip()
        
        if not text:
            i += 1
            continue
        
        # Skip file references and noise
        if is_file_reference(text) or is_metadata_or_noise(text):
            if debug:
                print(f"    [SKIP]: {text[:50]}")
            i += 1
            continue
        
        # Skip date/time stamps
        if is_date_or_time(text):
            if debug:
                print(f"    [DATE/TIME]: {text}")
            i += 1
            continue
        
        # Check if this is a standalone language marker (e.g., bold "DE" or "EN")
        standalone_lang = is_standalone_language_marker(text)
        if standalone_lang:
            current_lang = standalone_lang
            if current_lang not in current_content:
                current_content[current_lang] = []
            if debug:
                print(f"    [LANG]: {current_lang}")
            i += 1
            continue
        
        # Look ahead to check if this looks like a heading
        next_text = paragraphs[i + 1].text.strip() if i + 1 < len(paragraphs) else None
        
        # Check if this is a heading (topic)
        if looks_like_heading(text, next_text) and not is_bold_paragraph(para):
            # Save any existing content
            save_current_snippet()
            current_heading = text
            current_lang = None
            if debug:
                print(f"\n=== Heading: {text} ===")
            i += 1
            continue
        
        # Check for language marker at start of content (but be careful with "En date du..." etc.)
        lang, content = detect_language(text)
        # Only switch language if it's a clear language marker followed by content
        # Avoid false positives like "En date du..." (French) being detected as English
        if lang and content:
            # Check if this looks like a false positive
            # "En" followed by French/Italian/German words is likely not English
            if lang == "EN" and content and re.match(r"^(date|fait|vertu|effet|cas|plus|outre)\b", content, re.IGNORECASE):
                # This is likely French "En date de...", "En fait...", etc.
                # Keep current language and treat as continuation
                if current_lang:
                    current_content[current_lang].append(text)
                    if debug:
                        print(f"    [{current_lang}+]: {text[:50]}... (false EN)")
            else:
                current_lang = lang
                if current_lang not in current_content:
                    current_content[current_lang] = []
                current_content[current_lang].append(content)
                if debug:
                    preview = content[:50] + "..." if len(content) > 50 else content
                    print(f"    [{lang}]: {preview}")
        elif current_lang and current_heading:
            # Continue adding content to current language
            current_content[current_lang].append(text)
            if debug:
                preview = text[:50] + "..." if len(text) > 50 else text
                print(f"    [{current_lang}+]: {preview}")
        elif current_heading and not current_content:
            # Content without explicit language marker - default to DE
            current_lang = "DE"
            if "DE" not in current_content:
                current_content["DE"] = []
            current_content["DE"].append(text)
            if debug:
                print(f"    [DE-implicit]: {text[:50]}...")
        
        i += 1
    
    # Save any remaining content
    save_current_snippet()
    
    return snippets


def ensure_unique_titles(snippets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure all snippet titles are unique by adding suffixes if needed."""
    title_counts: dict[str, int] = {}
    
    for snippet in snippets:
        title = snippet["title"]
        if title in title_counts:
            title_counts[title] += 1
            snippet["title"] = f"{title}-{title_counts[title]}"
        else:
            title_counts[title] = 1
    
    return snippets


def add_linked_snippets(snippets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Add linked_snippets field to connect DE/FR/IT/EN versions of the same heading.
    """
    # Group snippets by category+heading
    groups: dict[str, list[dict[str, Any]]] = {}
    for snippet in snippets:
        meta = snippet.get("metadata", {})
        key = f"{meta.get('category', '')}|{meta.get('heading', '')}"
        if key not in groups:
            groups[key] = []
        groups[key].append(snippet)
    
    # Add linked_snippets to each snippet
    for group_snippets in groups.values():
        if len(group_snippets) > 1:
            titles = [s["title"] for s in group_snippets]
            for snippet in group_snippets:
                # Link to other language versions (excluding self)
                other_titles = [t for t in titles if t != snippet["title"]]
                if other_titles:
                    snippet["metadata"]["linked_snippets"] = other_titles
    
    return snippets


def main():
    parser = argparse.ArgumentParser(
        description="Extract snippets from Antwortvorlagen Actors.docx"
    )
    parser.add_argument(
        "--input", "-i",
        default="../../test-data/antwortvorlagen-actors/Antwortvorlagen Actors.docx",
        help="Path to input docx file"
    )
    parser.add_argument(
        "--output", "-o",
        default="../../test-data/antwortvorlagen-actors/extracted_snippets.json",
        help="Path to output JSON file"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug output"
    )
    args = parser.parse_args()
    
    # Resolve paths relative to script location
    script_dir = Path(__file__).parent
    input_path = (script_dir / args.input).resolve()
    output_path = (script_dir / args.output).resolve()
    
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1
    
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    
    # Extract snippets
    snippets = extract_document_structure(str(input_path), debug=args.debug)
    
    # Ensure unique titles
    snippets = ensure_unique_titles(snippets)
    
    # Add cross-references between language versions
    snippets = add_linked_snippets(snippets)
    
    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(snippets, f, ensure_ascii=False, indent=2)
    
    print(f"\nExtracted {len(snippets)} snippets")
    
    # Summary by language
    lang_counts: dict[str, int] = {}
    for s in snippets:
        lang = s.get("metadata", {}).get("language", "unknown")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    
    print("By language:")
    for lang, count in sorted(lang_counts.items()):
        print(f"  {lang}: {count}")
    
    # Summary of headings
    headings = set(s.get("metadata", {}).get("heading", "") for s in snippets)
    print(f"\nUnique headings: {len(headings)}")
    for h in sorted(headings)[:10]:
        print(f"  - {h}")
    if len(headings) > 10:
        print(f"  ... and {len(headings) - 10} more")
    
    print(f"\nJSON written to: {output_path}")
    return 0


if __name__ == "__main__":
    exit(main())
