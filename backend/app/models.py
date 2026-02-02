"""Pydantic request/response models."""
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


class SourceItem(BaseModel):
    id: str
    text: str
    title: str | None = None
    snippet_confidence: float = Field(..., ge=0, le=1)


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    answer_confidence: float = Field(..., ge=0, le=1)


class SnippetCreate(BaseModel):
    text: str = Field(..., min_length=1)
    title: str | None = None
    metadata: dict[str, str] | None = None


class SnippetItem(BaseModel):
    id: str
    text: str
    title: str | None = None
    metadata: dict[str, str] | None = None
    created_at: str | None = None


class SnippetListResponse(BaseModel):
    snippets: list[SnippetItem]
    total: int
