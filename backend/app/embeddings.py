"""Embedding model loading and encoding (sentence-transformers or Azure OpenAI)."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

_model = None
_azure_client = None


def _use_azure_embeddings():
    from .config import get_settings
    s = get_settings()
    endpoint = (s.azure_openai_endpoint or "").strip()
    key = (s.azure_openai_api_key or "").strip()
    deployment = (s.azure_openai_embedding_deployment or "").strip()
    if endpoint and key and deployment:
        return True
    if endpoint or key:
        logger.warning(
            "Azure endpoint/key set but AZURE_OPENAI_EMBEDDING_DEPLOYMENT missing or empty; using local embeddings. Set it in .env to use Azure for embeddings."
        )
    return False


def get_embedding_model():
    """Lazy-load sentence-transformers model (used when Azure embeddings not configured)."""
    global _model
    if _model is None:
        from .config import get_settings
        settings = get_settings()
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model: %s", settings.embedding_model)
            _model = SentenceTransformer(settings.embedding_model)
        except Exception as e:
            hint = ""
            if (settings.azure_openai_endpoint or "").strip() and (settings.azure_openai_api_key or "").strip():
                hint = " Set AZURE_OPENAI_EMBEDDING_DEPLOYMENT in .env to use Azure embeddings instead."
            raise RuntimeError(
                f"Failed to load local embedding model: {e}.{hint}"
            ) from e
    return _model


def _get_azure_embedding_client():
    """Lazy-create Azure OpenAI client for embeddings."""
    global _azure_client
    if _azure_client is None:
        from openai import AzureOpenAI
        from .config import get_settings
        s = get_settings()
        _azure_client = AzureOpenAI(
            api_key=s.azure_openai_api_key,
            api_version=s.azure_openai_api_version,
            azure_endpoint=s.azure_openai_endpoint,
        )
    return _azure_client


def embed(texts: list[str]) -> "np.ndarray":
    """Return embedding matrix of shape (len(texts), dim). Uses Azure OpenAI if configured, else sentence-transformers."""
    import numpy as np

    if _use_azure_embeddings():
        client = _get_azure_embedding_client()
        from .config import get_settings
        deployment = get_settings().azure_openai_embedding_deployment
        # Azure allows batch input; pass as list of strings
        response = client.embeddings.create(input=texts, model=deployment)
        # Preserve order (response.data may be ordered by index)
        by_index = {d.index: d.embedding for d in response.data}
        vectors = [by_index[i] for i in range(len(texts))]
        return np.array(vectors, dtype=np.float32)
    model = get_embedding_model()
    return model.encode(texts, convert_to_numpy=True)
