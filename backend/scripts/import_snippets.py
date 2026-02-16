#!/usr/bin/env python3
"""
Import snippets from JSON file via API.

Usage:
    python import_snippets.py --input FILE [--api-url URL] [--email EMAIL] [--password PASSWORD]
    python import_snippets.py --input FILE --clear-group GROUP_NAME  # Delete group before import
    python import_snippets.py --input FILE --clear-all  # Delete ALL snippets before import

The script will:
1. Login to get an access token (or use provided credentials)
2. Optionally delete existing snippets (--clear-group or --clear-all)
3. Read the JSON file with extracted snippets
4. Import snippets in batches via POST /api/snippets
"""
import argparse
import json
import sys
from pathlib import Path

import requests


def login(api_url: str, email: str, password: str) -> str | None:
    """Login and return access token."""
    url = f"{api_url}/api/auth/login"
    try:
        response = requests.post(url, json={"email": email, "password": password})
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Login request failed: {e}")
        return None


def get_snippets(api_url: str, token: str, group: str | None = None, limit: int = 1000) -> list[dict]:
    """Fetch existing snippets, optionally filtered by group."""
    headers = {"Authorization": f"Bearer {token}"}
    params = {"limit": limit}
    if group:
        params["group"] = group
    
    try:
        response = requests.get(f"{api_url}/api/snippets", headers=headers, params=params)
        if response.status_code == 200:
            return response.json().get("snippets", [])
        else:
            print(f"Failed to fetch snippets: {response.status_code} - {response.text}")
            return []
    except requests.RequestException as e:
        print(f"Fetch snippets request failed: {e}")
        return []


def delete_snippet(api_url: str, token: str, snippet_id: str) -> bool:
    """Delete a single snippet by ID."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.delete(f"{api_url}/api/snippets/{snippet_id}", headers=headers)
        return response.status_code == 200
    except requests.RequestException:
        return False


def clear_snippets(api_url: str, token: str, group: str | None = None, dry_run: bool = False) -> int:
    """Delete snippets. If group specified, only that group. Returns count deleted."""
    snippets = get_snippets(api_url, token, group=group)
    
    if not snippets:
        print(f"  No snippets found{f' in group {group!r}' if group else ''}")
        return 0
    
    if dry_run:
        print(f"  [DRY RUN] Would delete {len(snippets)} snippets{f' in group {group!r}' if group else ''}")
        return 0
    
    deleted = 0
    for i, snippet in enumerate(snippets):
        snippet_id = snippet.get("id")
        if snippet_id and delete_snippet(api_url, token, snippet_id):
            deleted += 1
            if (i + 1) % 10 == 0 or i == len(snippets) - 1:
                print(f"  Deleted {deleted}/{len(snippets)} snippets...")
        else:
            print(f"  Failed to delete snippet: {snippet_id}")
    
    return deleted


def _group_snippets_by_linked(snippets: list[dict], batch_size: int) -> list[list[dict]]:
    """Group snippets so that linked siblings always end up in the same batch.
    
    This ensures the backend's dedup logic (which works within a single API call)
    can correctly avoid generating duplicate translations for linked groups.
    """
    # Build linked groups using Union-Find on titles
    title_to_idx: dict[str, int] = {}
    for i, s in enumerate(snippets):
        title = s.get("title", "")
        if title:
            title_to_idx[title] = i

    # parent[i] = representative index for snippet i's linked group
    parent = list(range(len(snippets)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i, s in enumerate(snippets):
        linked = (s.get("metadata") or {}).get("linked_snippets", [])
        for linked_title in linked:
            if linked_title in title_to_idx:
                union(i, title_to_idx[linked_title])

    # Collect groups
    groups: dict[int, list[int]] = {}
    for i in range(len(snippets)):
        root = find(i)
        groups.setdefault(root, []).append(i)

    # Build batches keeping groups together
    batches: list[list[dict]] = []
    current_batch: list[dict] = []
    for group_indices in groups.values():
        group_items = [snippets[i] for i in group_indices]
        if current_batch and len(current_batch) + len(group_items) > batch_size:
            batches.append(current_batch)
            current_batch = []
        current_batch.extend(group_items)
    if current_batch:
        batches.append(current_batch)

    return batches


def import_snippets(
    api_url: str,
    token: str,
    snippets: list[dict],
    batch_size: int = 50,
    anonymize: bool = False,
    skip_translation: bool = False,
) -> tuple[int, list[str]]:
    """Import snippets in batches. Returns (success_count, errors).
    
    Linked snippets (siblings in different languages) are always kept in the same
    batch so the backend can deduplicate translations correctly.
    """
    url = f"{api_url}/api/snippets"
    headers = {"Authorization": f"Bearer {token}"}
    
    batches = _group_snippets_by_linked(snippets, batch_size)
    
    total_imported = 0
    errors = []
    
    for batch_num, batch in enumerate(batches, 1):
        for s in batch:
            if anonymize:
                s["anonymize"] = True
            if skip_translation:
                s["skip_translation"] = True
        try:
            response = requests.post(url, json=batch, headers=headers, timeout=600)
            if response.status_code == 200:
                result = response.json()
                count = result.get("count", len(batch))
                total_imported += count
                flags = []
                if anonymize:
                    flags.append("PII anonymized")
                if skip_translation:
                    flags.append("translation skipped")
                suffix = f" ({', '.join(flags)})" if flags else ""
                print(f"  Imported batch {batch_num}/{len(batches)}: {count} snippets{suffix}")
            else:
                error_msg = f"Batch {batch_num} failed: {response.status_code} - {response.text}"
                errors.append(error_msg)
                print(f"  {error_msg}")
        except requests.RequestException as e:
            error_msg = f"Batch {batch_num} request failed: {e}"
            errors.append(error_msg)
            print(f"  {error_msg}")
    
    return total_imported, errors


def main():
    parser = argparse.ArgumentParser(description="Import snippets from JSON file via API")
    parser.add_argument(
        "--input", "-i",
        default="../test-data/antwortvorlagen-actors/extracted_snippets.json",
        help="Path to JSON file with snippets (relative to current directory)"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--email",
        help="Admin email for login (or set ADMIN_EMAIL env var)"
    )
    parser.add_argument(
        "--password",
        help="Admin password for login (or set ADMIN_PASSWORD env var)"
    )
    parser.add_argument(
        "--token",
        help="Access token (skip login)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of snippets per batch (default: 50)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without actually importing"
    )
    parser.add_argument(
        "--clear-group",
        help="Delete all snippets in this group before importing"
    )
    parser.add_argument(
        "--clear-all",
        action="store_true",
        help="Delete ALL snippets before importing (use with caution!)"
    )
    parser.add_argument(
        "--anonymize",
        action="store_true",
        help="Anonymize PII (names, addresses, companies, etc.) before storing"
    )
    parser.add_argument(
        "--skip-translation",
        action="store_true",
        help="Skip LLM translation generation (use when JSON already contains all language versions)"
    )
    args = parser.parse_args()
    
    # Resolve input path
    # If path is absolute, use as-is; otherwise resolve from current working directory
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    input_path = input_path.resolve()
    
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1
    
    # Load snippets
    print(f"Loading snippets from: {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        snippets = json.load(f)
    
    print(f"Found {len(snippets)} snippets to import")
    
    # Show summary by language
    lang_counts: dict[str, int] = {}
    for s in snippets:
        lang = s.get("metadata", {}).get("language", "unknown")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    print("By language:")
    for lang, count in sorted(lang_counts.items()):
        print(f"  {lang}: {count}")
    
    # Check for conflicting clear options
    if args.clear_all and args.clear_group:
        print("Error: Cannot use both --clear-all and --clear-group")
        return 1
    
    if args.dry_run:
        print("\n[DRY RUN] Would import the above snippets.")
        print("Sample snippet:")
        if snippets:
            sample = snippets[0]
            print(f"  Title: {sample.get('title')}")
            print(f"  Group: {sample.get('group')}")
            print(f"  Text preview: {sample.get('text', '')[:100]}...")
            if sample.get("metadata", {}).get("linked_snippets"):
                print(f"  Linked snippets: {sample['metadata']['linked_snippets']}")
                print("  -> LLM translation will be SKIPPED (existing translations)")
    
    # Get auth token
    token = args.token
    if not token:
        import os
        email = args.email or os.environ.get("ADMIN_EMAIL")
        password = args.password or os.environ.get("ADMIN_PASSWORD")
        
        if not email or not password:
            print("Error: Provide --email and --password, or --token, or set ADMIN_EMAIL/ADMIN_PASSWORD env vars")
            return 1
        
        print(f"\nLogging in as: {email}")
        token = login(args.api_url, email, password)
        if not token:
            return 1
        print("Login successful")
    
    # Clear existing snippets if requested
    if args.clear_all:
        print("\nClearing ALL snippets...")
        if args.dry_run:
            clear_snippets(args.api_url, token, group=None, dry_run=True)
        else:
            deleted = clear_snippets(args.api_url, token, group=None)
            print(f"Deleted {deleted} snippets")
    elif args.clear_group:
        print(f"\nClearing snippets in group: {args.clear_group}")
        if args.dry_run:
            clear_snippets(args.api_url, token, group=args.clear_group, dry_run=True)
        else:
            deleted = clear_snippets(args.api_url, token, group=args.clear_group)
            print(f"Deleted {deleted} snippets from group '{args.clear_group}'")
    
    if args.dry_run:
        return 0
    
    # Import snippets
    flags = []
    if args.anonymize:
        flags.append("PII anonymization")
    if args.skip_translation:
        flags.append("translation skipped")
    flags_msg = f" ({', '.join(flags)})" if flags else ""
    print(f"\nImporting {len(snippets)} snippets to {args.api_url}{flags_msg}...")
    imported, errors = import_snippets(
        args.api_url, token, snippets, args.batch_size,
        anonymize=args.anonymize,
        skip_translation=args.skip_translation,
    )
    
    print(f"\nImport complete: {imported} snippets imported")
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors:
            print(f"  - {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
