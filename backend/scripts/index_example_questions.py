#!/usr/bin/env python3
"""
Index example questions for existing snippets.

This migration script indexes example questions from existing snippets into the 
new example_questions ChromaDB collection for hybrid retrieval.

Usage:
    # Index existing example questions only:
    python index_example_questions.py --direct
    
    # Generate example questions for snippets that don't have any (reverse HyDE):
    python index_example_questions.py --direct --generate-missing
    
    # Via API (requires authentication):
    python index_example_questions.py --api-url http://localhost:8000 --email admin@example.com --password yourpass
    
    # Dry run (show what would be indexed without making changes):
    python index_example_questions.py --direct --dry-run
    python index_example_questions.py --direct --generate-missing --dry-run

The script will:
1. Fetch all existing snippets
2. Find snippets with example_questions in metadata and index them
3. Optionally (--generate-missing): Generate example questions for snippets without them using LLM
"""
import argparse
import sys
from pathlib import Path

# Add parent to path for imports when running directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def index_via_direct_access(dry_run: bool = False, generate_missing: bool = False) -> int:
    """Index example questions using direct database access.
    
    Args:
        dry_run: If True, show what would be done without making changes
        generate_missing: If True, generate example questions for snippets that don't have any
    """
    from app.store import (
        list_snippets,
        _index_example_questions,
        _delete_example_questions,
        _get_example_questions_collection,
        update_snippet,
    )
    
    # Import generation function if needed
    if generate_missing:
        from app.generation import generate_example_question
    
    print("Fetching all snippets (including translations)...")
    snippets, total = list_snippets(limit=100000, include_translations=True)
    print(f"Found {total} snippets (including translations)")
    
    # Count existing example questions
    eq_coll = _get_example_questions_collection()
    existing_count = eq_coll.count()
    print(f"Existing example questions in collection: {existing_count}")
    
    if generate_missing:
        print("\nWill generate example questions for snippets without them (reverse HyDE)...")
    
    indexed_count = 0
    generated_count = 0
    skipped_count = 0
    
    for i, snippet in enumerate(snippets):
        snippet_id = snippet["id"]
        metadata = snippet.get("metadata") or {}
        example_questions = metadata.get("example_questions", [])
        title = snippet.get("title") or ""
        group = snippet.get("group") or ""
        text = snippet.get("text") or ""
        
        # Filter out empty questions
        questions = [q.strip() for q in example_questions if q and q.strip()] if example_questions else []
        
        if questions:
            # Snippet has example questions - index them
            if dry_run:
                print(f"  [DRY RUN] Would index {len(questions)} existing questions for '{title}' ({snippet_id})")
                for j, q in enumerate(questions):
                    print(f"    {j+1}. {q[:60]}{'...' if len(q) > 60 else ''}")
            else:
                _delete_example_questions(snippet_id)
                _index_example_questions(snippet_id, questions, title, group)
                print(f"  Indexed {len(questions)} existing questions for '{title}' ({snippet_id})")
            indexed_count += 1
            
        elif generate_missing and text:
            # No example questions - generate one using LLM
            # Check if this is an auto-translated snippet (ID contains _tr_)
            is_auto_translation = "_tr_" in snippet_id
            
            if dry_run:
                print(f"  [DRY RUN] Would generate example question for '{title}' ({snippet_id})")
            else:
                print(f"  Generating question for '{title}' ({snippet_id})...", end=" ", flush=True)
                generated_q = generate_example_question(text, title)
                if generated_q:
                    _delete_example_questions(snippet_id)
                    _index_example_questions(snippet_id, [generated_q], title, group)
                    
                    # Save to snippet metadata (only for original snippets, not auto-translations)
                    if not is_auto_translation:
                        new_metadata = {**metadata, "example_questions": [generated_q]}
                        update_snippet(
                            snippet_id,
                            text=text,
                            title=title,
                            metadata=new_metadata,
                            group=group,
                            skip_translation=True,  # Don't regenerate translations
                        )
                    
                    print(f"OK: '{generated_q[:50]}{'...' if len(generated_q) > 50 else ''}'")
                    generated_count += 1
                else:
                    print("FAILED (no LLM response)")
                    skipped_count += 1
        else:
            skipped_count += 1
    
    print(f"\nSummary:")
    print(f"  Total snippets: {total}")
    print(f"  Snippets with existing example questions indexed: {indexed_count}")
    if generate_missing:
        print(f"  Snippets with generated example questions: {generated_count}")
    print(f"  Snippets skipped (no questions, no generation): {skipped_count}")
    
    if not dry_run:
        new_count = eq_coll.count()
        print(f"  Total example questions in collection: {new_count}")
    
    return indexed_count + generated_count


def index_via_api(api_url: str, email: str, password: str, dry_run: bool = False, generate_missing: bool = False) -> int:
    """Index example questions via API by triggering snippet updates.
    
    Note: When generate_missing=True, this uses direct access for generation
    since the API doesn't have a generate endpoint yet.
    """
    import requests
    
    # Login
    print(f"Logging in to {api_url}...")
    login_url = f"{api_url}/api/auth/login"
    try:
        response = requests.post(login_url, json={"email": email, "password": password})
        if response.status_code != 200:
            print(f"Login failed: {response.status_code} - {response.text}")
            return 0
        token = response.json().get("access_token")
    except requests.RequestException as e:
        print(f"Login request failed: {e}")
        return 0
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Import generation function if needed
    if generate_missing:
        from app.generation import generate_example_question
    
    # Fetch all snippets
    print("Fetching all snippets...")
    snippets_url = f"{api_url}/api/snippets?limit=10000"
    try:
        response = requests.get(snippets_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch snippets: {response.status_code} - {response.text}")
            return 0
        data = response.json()
        snippets = data.get("snippets", [])
        total = data.get("total", len(snippets))
    except requests.RequestException as e:
        print(f"Failed to fetch snippets: {e}")
        return 0
    
    print(f"Found {total} snippets")
    
    if generate_missing:
        print("\nWill generate example questions for snippets without them (reverse HyDE)...")
    
    indexed_count = 0
    generated_count = 0
    
    for snippet in snippets:
        snippet_id = snippet["id"]
        metadata = snippet.get("metadata") or {}
        example_questions = metadata.get("example_questions", [])
        title = snippet.get("title") or ""
        text = snippet.get("text") or ""
        
        # Filter out empty questions
        questions = [q.strip() for q in example_questions if q and q.strip()] if example_questions else []
        
        if questions:
            # Has existing questions - trigger update to re-index
            if dry_run:
                print(f"  [DRY RUN] Would trigger update for '{title}' ({snippet_id}) with {len(questions)} questions")
            else:
                update_url = f"{api_url}/api/snippets/{snippet_id}"
                try:
                    update_data = {
                        "text": text,
                        "title": title,
                        "metadata": metadata,
                        "group": snippet.get("group") or "",
                    }
                    response = requests.put(update_url, json=update_data, headers=headers)
                    if response.status_code == 200:
                        print(f"  Updated '{title}' ({snippet_id}) - {len(questions)} questions indexed")
                    else:
                        print(f"  Failed to update '{title}': {response.status_code}")
                except requests.RequestException as e:
                    print(f"  Failed to update '{title}': {e}")
            indexed_count += 1
            
        elif generate_missing and text:
            # No questions - generate one and update via API
            if dry_run:
                print(f"  [DRY RUN] Would generate and update '{title}' ({snippet_id})")
            else:
                print(f"  Generating question for '{title}' ({snippet_id})...", end=" ", flush=True)
                generated_q = generate_example_question(text, title)
                if generated_q:
                    # Update snippet with generated question
                    new_metadata = {**metadata, "example_questions": [generated_q]}
                    update_url = f"{api_url}/api/snippets/{snippet_id}"
                    try:
                        update_data = {
                            "text": text,
                            "title": title,
                            "metadata": new_metadata,
                            "group": snippet.get("group") or "",
                        }
                        response = requests.put(update_url, json=update_data, headers=headers)
                        if response.status_code == 200:
                            print(f"OK: '{generated_q[:50]}{'...' if len(generated_q) > 50 else ''}'")
                            generated_count += 1
                        else:
                            print(f"FAILED to update: {response.status_code}")
                    except requests.RequestException as e:
                        print(f"FAILED: {e}")
                else:
                    print("FAILED (no LLM response)")
    
    print(f"\nSummary:")
    print(f"  Total snippets: {total}")
    print(f"  Snippets with existing questions updated: {indexed_count}")
    if generate_missing:
        print(f"  Snippets with generated questions: {generated_count}")
    
    return indexed_count + generated_count


def main():
    parser = argparse.ArgumentParser(
        description="Index example questions for existing snippets (migration script)"
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use direct database access (recommended for initial migration)",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--email",
        help="Admin email for API authentication",
    )
    parser.add_argument(
        "--password",
        help="Admin password for API authentication",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be indexed without making changes",
    )
    parser.add_argument(
        "--generate-missing",
        action="store_true",
        help="Generate example questions for snippets that don't have any (reverse HyDE)",
    )
    
    args = parser.parse_args()
    
    if args.direct:
        print("Using direct database access...")
        count = index_via_direct_access(dry_run=args.dry_run, generate_missing=args.generate_missing)
    elif args.email and args.password:
        print("Using API access...")
        count = index_via_api(args.api_url, args.email, args.password, dry_run=args.dry_run, generate_missing=args.generate_missing)
    else:
        print("Error: Either --direct or --email/--password must be provided")
        parser.print_help()
        sys.exit(1)
    
    if args.dry_run:
        print(f"\n[DRY RUN] Would have processed example questions for {count} snippets")
    else:
        print(f"\nDone! Processed example questions for {count} snippets")


if __name__ == "__main__":
    main()
