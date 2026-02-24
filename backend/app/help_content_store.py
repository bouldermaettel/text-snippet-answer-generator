"""Persisted help/manual HTML content for the top-level Help tab."""
from __future__ import annotations

from pathlib import Path

from .config import get_settings


def _help_content_path() -> Path:
    path = get_settings().data_dir / "help-content.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _default_help_path() -> Path:
    # Repository root from backend/app/help_content_store.py
    return Path(__file__).resolve().parents[2] / "BENUTZERHANDBUCH.html"


def _default_help_content() -> str:
    default_path = _default_help_path()
    if default_path.is_file():
        return default_path.read_text(encoding="utf-8")
    return (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"utf-8\"><title>Help</title></head><body>\n"
        "<h1>Help</h1>\n"
        "<p>No default help content was found. An admin can add it from the Help tab.</p>\n"
        "</body></html>\n"
    )


def get_help_content() -> str:
    """Return persisted help HTML, or default manual content if unset."""
    path = _help_content_path()
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return _default_help_content()


def set_help_content(content: str) -> None:
    """Persist help HTML content."""
    path = _help_content_path()
    path.write_text(content, encoding="utf-8")
