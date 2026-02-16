import { useState } from "react";
import { updateSnippet } from "../api";
import type { SnippetItem, SnippetMetadata } from "../types";
import { GroupSelector } from "./GroupSelector";

const LANGUAGES = [
  { code: "", label: "Auto-detect" },
  { code: "de", label: "German (DE)" },
  { code: "en", label: "English (EN)" },
  { code: "fr", label: "French (FR)" },
  { code: "it", label: "Italian (IT)" },
];

type Props = { snippet: SnippetItem; groups: string[]; onSaved: () => void; onCancel: () => void };

export function EditSnippetModal({ snippet, groups, onSaved, onCancel }: Props) {
  const [title, setTitle] = useState(snippet.title ?? "");
  const [text, setText] = useState(snippet.text);
  const [group, setGroup] = useState(snippet.group ?? "");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Metadata fields
  const [language, setLanguage] = useState((snippet.metadata?.language as string) ?? "");
  const [heading, setHeading] = useState((snippet.metadata?.heading as string) ?? "");
  const [category, setCategory] = useState((snippet.metadata?.category as string) ?? "");
  const [linkedSnippets, setLinkedSnippets] = useState(
    Array.isArray(snippet.metadata?.linked_snippets)
      ? (snippet.metadata.linked_snippets as string[]).join(", ")
      : ""
  );
  const [exampleQuestions, setExampleQuestions] = useState(
    Array.isArray(snippet.metadata?.example_questions)
      ? (snippet.metadata.example_questions as string[]).join("\n")
      : ""
  );

  function buildMetadata(): SnippetMetadata {
    const meta: Record<string, unknown> = { ...snippet.metadata };
    
    // Update or remove fields based on input
    if (language.trim()) meta.language = language.trim().toLowerCase();
    else delete meta.language;
    
    if (heading.trim()) meta.heading = heading.trim();
    else delete meta.heading;
    
    if (category.trim()) meta.category = category.trim();
    else delete meta.category;
    
    // Parse linked snippets
    const linked = linkedSnippets
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    if (linked.length > 0) meta.linked_snippets = linked;
    else delete meta.linked_snippets;
    
    // Parse example questions
    const questions = exampleQuestions
      .split("\n")
      .map((q) => q.trim())
      .filter((q) => q.length > 0);
    if (questions.length > 0) meta.example_questions = questions;
    else delete meta.example_questions;
    
    // Keep other existing metadata fields (like source_document_url)
    return Object.keys(meta).length > 0 ? meta : null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setMessage(null);
    setLoading(true);
    try {
      const metadata = buildMetadata();
      await updateSnippet(snippet.id, text.trim(), title.trim() || undefined, group.trim() || null, metadata);
      onSaved();
    } catch (err) {
      setMessage({
        type: "err",
        text: err instanceof Error ? err.message : "Failed to update snippet.",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-900/60 p-4"
      onClick={(e) => e.target === e.currentTarget && onCancel()}
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-snippet-modal-title"
    >
      <div
        className="my-8 w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-700">
          <h2 id="edit-snippet-modal-title" className="text-lg font-semibold text-slate-900 dark:text-white">
            Edit snippet
          </h2>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-300"
            aria-label="Close"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-4">
          <div>
            <label htmlFor="edit-snippet-title" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Title (optional)
            </label>
            <input
              id="edit-snippet-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Refund policy"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            />
          </div>
          
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="edit-snippet-group" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Group (optional)
              </label>
              <GroupSelector
                id="edit-snippet-group"
                groups={groups}
                value={group}
                onChange={setGroup}
                placeholder="e.g. Policies"
              />
            </div>
            <div>
              <label htmlFor="edit-snippet-language" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Language
              </label>
              <select
                id="edit-snippet-language"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="edit-snippet-text" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Text
            </label>
            <textarea
              id="edit-snippet-text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste or type the standard answer text…"
              rows={4}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
              required
            />
          </div>

          {/* Advanced metadata toggle */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
          >
            <svg
              className={`h-4 w-4 transition-transform ${showAdvanced ? "rotate-90" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            Advanced metadata
          </button>

          {showAdvanced && (
            <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/50">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="edit-snippet-heading" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Heading (optional)
                  </label>
                  <input
                    id="edit-snippet-heading"
                    type="text"
                    value={heading}
                    onChange={(e) => setHeading(e.target.value)}
                    placeholder="e.g. Customer Support"
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                  />
                </div>
                <div>
                  <label htmlFor="edit-snippet-category" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Category (optional)
                  </label>
                  <input
                    id="edit-snippet-category"
                    type="text"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    placeholder="e.g. General"
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                  />
                </div>
              </div>
              <div>
                <label htmlFor="edit-snippet-linked" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Linked snippets (optional)
                </label>
                <input
                  id="edit-snippet-linked"
                  type="text"
                  value={linkedSnippets}
                  onChange={(e) => setLinkedSnippets(e.target.value)}
                  placeholder="Comma-separated titles, e.g. snippet-en, snippet-fr"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                />
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Enter titles of related snippets in other languages
                </p>
              </div>
              <div>
                <label htmlFor="edit-snippet-questions" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Example questions (optional)
                </label>
                <textarea
                  id="edit-snippet-questions"
                  value={exampleQuestions}
                  onChange={(e) => setExampleQuestions(e.target.value)}
                  placeholder="Enter example questions that should match this snippet (one per line)..."
                  rows={2}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                />
              </div>
            </div>
          )}

          {message && (
            <p
              className={
                message.type === "ok"
                  ? "text-sm text-emerald-600 dark:text-emerald-400"
                  : "text-sm text-red-600 dark:text-red-400"
              }
            >
              {message.text}
            </p>
          )}
          <div className="flex justify-end gap-2 border-t border-slate-200 pt-4 dark:border-slate-700">
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !text.trim()}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 dark:bg-indigo-500 dark:hover:bg-indigo-600"
            >
              {loading ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
