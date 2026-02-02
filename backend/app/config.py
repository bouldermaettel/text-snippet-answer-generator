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

    model_config = {"env_file": _BACKEND_DIR / ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
