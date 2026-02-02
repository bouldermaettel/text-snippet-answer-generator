import { useState } from "react";
import { ask } from "./api";
import type { AskResponse } from "./types";
import { AddSnippetForm } from "./components/AddSnippetForm";
import { AnswerCard } from "./components/AnswerCard";
import { QuestionInput } from "./components/QuestionInput";

export default function App() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [showAddSnippet, setShowAddSnippet] = useState(false);

  async function handleAsk() {
    const q = question.trim();
    if (!q) return;
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const data = await ask(q);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
        <header className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white sm:text-3xl">
            Snippet Answer
          </h1>
          <p className="mt-2 text-slate-600 dark:text-slate-400">
            Ask a question. Answers are built from your snippet library with sources and confidence.
          </p>
        </header>

        <div className="mb-8">
          <QuestionInput
            value={question}
            onChange={setQuestion}
            onSubmit={handleAsk}
            loading={loading}
          />
        </div>

        {error && (
          <div
            className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200"
            role="alert"
          >
            {error}
          </div>
        )}

        {loading && (
          <div className="flex justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent dark:border-indigo-400 dark:border-t-transparent" />
          </div>
        )}

        {!loading && result && <AnswerCard data={result} />}

        {!loading && !result && !error && (
          <p className="text-center text-slate-500 dark:text-slate-400">
            Enter a question above to get an answer from your snippets.
          </p>
        )}

        <div className="mt-12 border-t border-slate-200 pt-8 dark:border-slate-700">
          <button
            type="button"
            onClick={() => setShowAddSnippet((s) => !s)}
            className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
          >
            {showAddSnippet ? "Hide" : "Add snippet"} to the knowledge base
          </button>
          {showAddSnippet && (
            <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800/50">
              <AddSnippetForm />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
