import { useCallback, useEffect, useState } from "react";
import { listPrompts, updatePrompt, resetPrompt } from "../api";
import type { PromptItem } from "../types";

function PromptCard({
  prompt,
  onSaved,
}: {
  prompt: PromptItem;
  onSaved: (updated: PromptItem) => void;
}) {
  const [draft, setDraft] = useState(prompt.template);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  const dirty = draft !== prompt.template;

  useEffect(() => {
    setDraft(prompt.template);
  }, [prompt.template]);

  useEffect(() => {
    if (!message) return;
    const t = setTimeout(() => setMessage(null), 3000);
    return () => clearTimeout(t);
  }, [message]);

  async function handleSave() {
    setSaving(true);
    setMessage(null);
    try {
      const updated = await updatePrompt(prompt.key, draft);
      onSaved(updated);
      setMessage({ type: "ok", text: "Saved" });
    } catch (e) {
      setMessage({ type: "err", text: e instanceof Error ? e.message : "Save failed" });
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    setResetting(true);
    setMessage(null);
    try {
      const updated = await resetPrompt(prompt.key);
      onSaved(updated);
      setDraft(updated.template);
      setMessage({ type: "ok", text: "Reset to default" });
    } catch (e) {
      setMessage({ type: "err", text: e instanceof Error ? e.message : "Reset failed" });
    } finally {
      setResetting(false);
    }
  }

  const rows = Math.max(4, draft.split("\n").length + 1);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800/50">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
            {prompt.label}
            {!prompt.is_default && (
              <span className="ml-2 inline-block rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
                customised
              </span>
            )}
          </h3>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            {prompt.description}
          </p>
        </div>
      </div>

      {prompt.placeholders.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          {prompt.placeholders.map((ph) => (
            <span
              key={ph}
              className="inline-block rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-mono text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300"
            >
              {ph}
            </span>
          ))}
        </div>
      )}

      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={rows}
        className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 font-mono text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:border-indigo-400 dark:focus:ring-indigo-400/20"
      />

      <div className="mt-2 flex items-center gap-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={!dirty || saving}
          className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 dark:bg-indigo-500 dark:hover:bg-indigo-600"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        <button
          type="button"
          onClick={handleReset}
          disabled={prompt.is_default || resetting}
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
        >
          {resetting ? "Resetting…" : "Reset to default"}
        </button>
        {message && (
          <span
            className={`text-sm font-medium ${
              message.type === "ok"
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-red-600 dark:text-red-400"
            }`}
          >
            {message.text}
          </span>
        )}
      </div>
    </div>
  );
}

export function PromptsView() {
  const [prompts, setPrompts] = useState<PromptItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const loadPrompts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listPrompts();
      setPrompts(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load prompts");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPrompts();
  }, [loadPrompts]);

  function handleSaved(updated: PromptItem) {
    setPrompts((prev) =>
      prev.map((p) => (p.key === updated.key ? updated : p))
    );
  }

  const mainPrompts = prompts.filter((p) => p.group === "Main Prompts");
  const advancedPrompts = prompts.filter((p) => p.group !== "Main Prompts");

  return (
    <>
      <h2 className="mb-2 text-xl font-semibold text-slate-900 dark:text-white">
        Prompt templates
      </h2>
      <p className="mb-6 text-slate-600 dark:text-slate-400">
        Customise the LLM prompts used for answer generation. Placeholders in curly braces are filled in automatically at runtime.
      </p>

      {error && (
        <div
          className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200"
          role="alert"
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-8">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent dark:border-indigo-400 dark:border-t-transparent" />
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {mainPrompts.map((p) => (
              <PromptCard key={p.key} prompt={p} onSaved={handleSaved} />
            ))}
          </div>

          {advancedPrompts.length > 0 && (
            <div className="mt-8">
              <button
                type="button"
                onClick={() => setAdvancedOpen(!advancedOpen)}
                className="flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
              >
                <svg
                  className={`h-4 w-4 shrink-0 transition-transform ${advancedOpen ? "rotate-90" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                Advanced prompts ({advancedPrompts.length})
              </button>
              {advancedOpen && (
                <div className="mt-4 space-y-4">
                  {advancedPrompts.map((p) => (
                    <PromptCard key={p.key} prompt={p} onSaved={handleSaved} />
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </>
  );
}
