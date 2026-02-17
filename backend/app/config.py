"""Application configuration from environment."""
from pathlib import Path

from pydantic_settings import BaseSettings

# .env next to backend/ (parent of app/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """App settings. Prefer env vars; .env is loaded automatically."""

    # Chroma / data
    chroma_persist_dir: str = "data/chroma"
    data_dir: Path = Path("data")
    # Where to save uploaded PDF/DOCX (default: data/uploads). Set empty to disable.
    upload_dir: str = "data/uploads"

    # Embeddings: local by default
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    use_openai_embeddings: bool = False
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-ada-002"

    # LLM: Azure OpenAI or Ollama (local)
    # Azure OpenAI (takes precedence if set)
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_chat_deployment: str = "gpt-35-turbo"
    azure_openai_embedding_deployment: str | None = None
    azure_openai_api_version: str = "2024-02-15-preview"

    # Ollama (used when Azure is not configured and Ollama is available)
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2"

    # Which LLM to use: "azure" | "ollama" | "none" (none = no LLM, use top snippet)
    # If "auto": use Azure if azure_openai_api_key set, else Ollama if ollama_base_url reachable, else "none"
    llm_provider: str = "auto"

    # HyDE: allow hypothetical answer for retrieval (only used when LLM is available)
    hyde_enabled: bool = True

    # Example question search: hybrid retrieval using embedded example questions
    enable_example_question_search: bool = True
    example_question_search_weight: float = 0.3  # weight for example question score in fusion (0.0-1.0)

    # PII anonymization: replace sensitive data (names, addresses, etc.) with placeholders
    enable_pii_anonymization: bool = True

    # Translation indexing: store translated versions of snippets for cross-language retrieval
    enable_translation_indexing: bool = True
    translation_languages: str = "en,de,fr,it"  # comma-separated list of target languages

    # Chunking: snippets longer than this (chars) are split; overlap between chunks
    chunk_size: int = 1500
    chunk_overlap: int = 200

    # CORS: comma-separated origins, "*" for all, or empty to auto-detect
    # In single-container mode (frontend served from same origin) CORS is not needed.
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Production mode flag (set to "production" in deployment)
    environment: str = "development"

    # Auth: JWT and initial admin (for seeding)
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 86400  # 24h
    admin_email: str | None = None
    admin_password: str | None = None
    database_url: str = "data/users.db"

    model_config = {"env_file": _BACKEND_DIR / ".env", "extra": "ignore"}

    def get_translation_languages(self) -> list[str]:
        """Return translation_languages as a list."""
        if not self.translation_languages:
            return []
        return [lang.strip().lower() for lang in self.translation_languages.split(",") if lang.strip()]


def get_settings() -> Settings:
    return Settings()
