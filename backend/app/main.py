"""FastAPI app: /api/ask, /api/snippets."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .generation import generate_answer
from .models import (
    AskRequest,
    AskResponse,
    SourceItem,
    SnippetCreate,
    SnippetItem,
    SnippetListResponse,
)
from .retrieval import answer_confidence, retrieve_and_score
from .store import add_snippets, list_snippets


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="RAG Snippet Answer API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest):
    """Retrieve relevant snippets, generate answer, return answer + sources + confidence."""
    sources = retrieve_and_score(req.question, top_k=5)
    if not sources:
        return AskResponse(
            answer="No relevant snippets in the knowledge base. Add snippets first.",
            sources=[],
            answer_confidence=0.0,
        )
    snippet_texts = [s["text"] for s in sources]
    answer_text = generate_answer(req.question, snippet_texts, settings=get_settings())
    confidences = [s["snippet_confidence"] for s in sources]
    ans_conf = answer_confidence(confidences)
    return AskResponse(
        answer=answer_text,
        sources=[SourceItem(
            id=s["id"],
            text=s["text"],
            title=s.get("title"),
            snippet_confidence=s["snippet_confidence"],
        ) for s in sources],
        answer_confidence=ans_conf,
    )


@app.get("/api/snippets", response_model=SnippetListResponse)
def get_snippets(limit: int = 100, offset: int = 0):
    """List snippets (paginated)."""
    snippets, total = list_snippets(limit=limit, offset=offset)
    return SnippetListResponse(
        snippets=[SnippetItem(id=s["id"], text=s["text"], title=s.get("title"), metadata=s.get("metadata")) for s in snippets],
        total=total,
    )


@app.post("/api/snippets")
def post_snippets(payload: SnippetCreate | list[SnippetCreate]):
    """Add one or more snippets."""
    if isinstance(payload, list):
        items = [{"text": p.text, "title": p.title, "metadata": p.metadata} for p in payload]
    else:
        items = [{"text": payload.text, "title": payload.title, "metadata": payload.metadata}]
    ids = add_snippets(items)
    return {"ids": ids, "count": len(ids)}


@app.get("/health")
def health():
    return {"status": "ok"}
