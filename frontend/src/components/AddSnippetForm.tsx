import { useState } from "react";
import { addSnippet } from "../api";
import { GroupSelector } from "./GroupSelector";

const LANGUAGES = [
  { code: "", label: "Auto-detect" },
  { code: "de", label: "German (DE)" },
  { code: "en", label: "English (EN)" },
  { code: "fr", label: "French (FR)" },
  { code: "it", label: "Italian (IT)" },
];

type Props = { onAdded?: () => void; defaultGroup?: string; groups: string[] };

export function AddSnippetForm({ onAdded, defaultGroup, groups }: Props) {
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [group, setGroup] = useState(defaultGroup ?? "");
  const [language, setLanguage] = useState("");
  const [heading, setHeading] = useState("");
  const [category, setCategory] = useState("");
  const [linkedSnippets, setLinkedSnippets] = useState("");
  const [anonymize, setAnonymize] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setMessage(null);
    setLoading(true);
    try {
      // Build metadata object
      const metadata: { language?: string; heading?: string; category?: string; linked_snippets?: string[] } = {};
      if (language) metadata.language = language;
      if (heading.trim()) metadata.heading = heading.trim();
      if (category.trim()) metadata.category = category.trim();
      if (linkedSnippets.trim()) {
        metadata.linked_snippets = linkedSnippets
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      }

      await addSnippet(
        text.trim(),
        title.trim() || undefined,
        group.trim() || null,
        Object.keys(metadata).length > 0 ? metadata : undefined,
        anonymize
      );
      setMessage({ type: "ok", text: anonymize ? "Snippet added (PII anonymized)." : "Snippet added." });
      setText("");
      setTitle("");
      setGroup(defaultGroup ?? "");
      setLanguage("");
      setHeading("");
      setCategory("");
      setLinkedSnippets("");
      onAdded?.();
    } catch (err) {
      setMessage({ type: "err", text: err instanceof Error ? err.message : "Failed to add snippet." });
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label htmlFor="snippet-title" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
          Title (optional)
        </label>
        <input
          id="snippet-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Refund policy"
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
        />
      </div>
      
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="snippet-group" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
            Group (optional)
          </label>
          <GroupSelector
            id="snippet-group"
            groups={groups}
            value={group}
            onChange={setGroup}
            placeholder="e.g. Policies"
          />
        </div>
        <div>
          <label htmlFor="snippet-language" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
            Language
          </label>
          <select
            id="snippet-language"
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
        <label htmlFor="snippet-text" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
          Text
        </label>
        <textarea
          id="snippet-text"
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
              <label htmlFor="snippet-heading" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Heading (optional)
              </label>
              <input
                id="snippet-heading"
                type="text"
                value={heading}
                onChange={(e) => setHeading(e.target.value)}
                placeholder="e.g. Customer Support"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
              />
            </div>
            <div>
              <label htmlFor="snippet-category" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Category (optional)
              </label>
              <input
                id="snippet-category"
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="e.g. General"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
              />
            </div>
          </div>
          <div>
            <label htmlFor="snippet-linked" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Linked snippets (optional)
            </label>
            <input
              id="snippet-linked"
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
        </div>
      )}

      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
          <input
            type="checkbox"
            checked={anonymize}
            onChange={(e) => setAnonymize(e.target.checked)}
            className="h-4 w-4 rounded border-slate-300 text-slate-700 focus:ring-slate-500 dark:border-slate-600 dark:bg-slate-700"
          />
          <span>Anonymize PII</span>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            (names, addresses, etc.)
          </span>
        </label>
        <button
          type="submit"
          disabled={loading || !text.trim()}
          className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50 dark:bg-slate-600 dark:hover:bg-slate-700"
        >
          {loading ? "Adding…" : "Add snippet"}
        </button>
      </div>
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
    </form>
  );
}
