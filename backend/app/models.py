"""Pydantic request/response models."""
from typing import Any

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    group_names: list[str] | None = None  # limit search to these groups
    snippet_ids: list[str] | None = None  # limit search to these logical snippet ids
    languages: list[str] | None = None  # limit search to these languages (e.g., ["de", "en"])
    answer_closeness: float = Field(0.5, ge=0, le=1)  # 0=free, 1=stick to snippet wording
    use_hyde: bool = False  # use hypothetical answer embedding for retrieval
    use_keyword_rerank: bool = True  # rerank by keyword overlap after vector search


class SourceItem(BaseModel):
    id: str
    text: str
    title: str | None = None
    snippet_confidence: float = Field(..., ge=0, le=1)
    source_document_url: str | None = None
    section_label: str | None = None
    metadata: dict[str, Any] | None = None  # includes language, heading, category, etc.


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    answer_confidence: float = Field(..., ge=0, le=1)


class SnippetCreate(BaseModel):
    text: str = Field(..., min_length=1)
    title: str | None = None
    metadata: dict[str, Any] | None = None  # supports example_questions: list[str], language: str, etc.
    group: str | None = None
    anonymize: bool = False  # if True, PII is replaced with generic placeholders before storing
    skip_translation: bool = False  # if True, skip LLM translation generation (useful when translations already exist)


class SnippetUpdate(BaseModel):
    text: str = Field(..., min_length=1)
    title: str | None = None
    group: str | None = None
    metadata: dict[str, Any] | None = None  # supports example_questions: list[str], language: str, etc.


class ExampleQuestionsUpdate(BaseModel):
    """Update example questions for a snippet (original or translation)."""
    example_questions: list[str] = Field(default_factory=list)


class SnippetItem(BaseModel):
    id: str
    text: str
    title: str | None = None
    group: str | None = None
    metadata: dict[str, Any] | None = None  # supports example_questions: list[str], language: str, etc.
    created_at: str | None = None


class SnippetListResponse(BaseModel):
    snippets: list[SnippetItem]
    total: int


# Auth / user management
class UserCreate(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    status: str = "active"
    created_at: str | None = None


class UserStatusUpdate(BaseModel):
    """Admin sets user status (e.g. approve = active)."""
    status: str  # "active"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreateAdmin(BaseModel):
    """Admin creates a user (email, password, optional role)."""
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)
    role: str = "user"


class RefineRequest(BaseModel):
    """Request to refine an existing answer with user feedback."""
    original_question: str = Field(..., min_length=1)
    original_answer: str = Field(..., min_length=1)
    refinement_prompt: str = Field(..., min_length=1)
    selected_source_ids: list[str] = Field(default_factory=list)  # IDs of sources to include in context
    sources: list[SourceItem] = Field(default_factory=list)  # Full source items from original response
    answer_closeness: float = Field(0.5, ge=0, le=1)


class RefineResponse(BaseModel):
    """Response with refined answer."""
    answer: str
    sources: list[SourceItem]  # Sources that were used (selected ones)
    answer_confidence: float = Field(..., ge=0, le=1)
