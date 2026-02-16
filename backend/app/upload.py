"""Extract plain text from uploaded .txt, .docx, and .pdf files."""
from __future__ import annotations

from io import BytesIO

from docx import Document as DocxDocument
from pypdf import PdfReader


def extract_text_from_bytes(content: bytes, filename: str) -> str:
    """Extract plain text from file content. Supports .txt, .docx, and .pdf."""
    name = (filename or "").lower()
    if name.endswith(".txt"):
        return content.decode("utf-8", errors="replace").strip()
    if name.endswith(".docx"):
        doc = DocxDocument(BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    if name.endswith(".pdf"):
        reader = PdfReader(BytesIO(content))
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n\n".join(parts).strip()
    raise ValueError(f"Unsupported file type: {filename}. Use .txt, .docx, or .pdf")
