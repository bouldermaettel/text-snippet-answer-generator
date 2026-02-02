# Snippet Answer – RAG Q&A MVP

Answer questions from a growing collection of text snippets. Uses semantic search + optional LLM (Azure OpenAI or Ollama) with source attribution and confidence scores.

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env        # optional: set AZURE_OPENAI_* or use Ollama
uvicorn app.main:app --reload --port 8000
```

- **LLM**: Set `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` for Azure, or run [Ollama](https://ollama.ai) locally (`ollama serve`, `ollama pull llama3.2`) for local answers. If neither is set, the app falls back to returning the top snippet as the answer.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Ask a question (add snippets first via “Add snippet” at the bottom).

### 3. Seed snippets (optional)

With the backend running:

```bash
cd backend
curl -X POST http://localhost:8000/api/snippets -H "Content-Type: application/json" -d '{"text":"Our refund window is 30 days from purchase. Contact support with your order ID.","title":"Refund policy"}'
curl -X POST http://localhost:8000/api/snippets -H "Content-Type: application/json" -d '{"text":"Shipping usually takes 3–5 business days within the EU.","title":"Shipping"}'
```

Then ask e.g. “What is your refund policy?” in the UI.

## Project layout

- `backend/app/` – FastAPI app, ChromaDB store, embeddings, retrieval, Azure/Ollama generation
- `frontend/` – React + Vite + TypeScript + Tailwind; ask UI, answer + sources + confidence, add snippet

## Troubleshooting

- **SSL / certificate errors** when downloading the embedding model from Hugging Face (e.g. behind a proxy or corporate network): set `SSL_CERT_FILE` or `REQUESTS_CA_BUNDLE` to your CA bundle, or pre-download the model once with a working connection and reuse the cache. The embedding model is loaded on first use (first ask or add-snippet), not at server startup.

## Environment (backend)

See `backend/.env.example`. Main options:

- **Azure OpenAI (LLM)**: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_CHAT_DEPLOYMENT`
- **Azure OpenAI (embeddings)**: set `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` (e.g. `text-embedding-3-small`) along with the same endpoint and API key to use Azure for snippet embeddings instead of the local sentence-transformers model.
- **Ollama**: `OLLAMA_BASE_URL` (default `http://localhost:11434`), `OLLAMA_CHAT_MODEL` (e.g. `llama3.2`)
- `LLM_PROVIDER`: `auto` (default), `azure`, `ollama`, or `none`
