import { useState } from "react";
import { addSnippet } from "../api";

type Props = { onAdded?: () => void };

export function AddSnippetForm({ onAdded }: Props) {
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setMessage(null);
    setLoading(true);
    try {
      await addSnippet(text.trim(), title.trim() || undefined);
      setMessage({ type: "ok", text: "Snippet added." });
      setText("");
      setTitle("");
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
      <button
        type="submit"
        disabled={loading || !text.trim()}
        className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50 dark:bg-slate-600 dark:hover:bg-slate-700"
      >
        {loading ? "Adding…" : "Add snippet"}
      </button>
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
