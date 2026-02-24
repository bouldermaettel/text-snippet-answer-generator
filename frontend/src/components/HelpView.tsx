import { useCallback, useEffect, useState } from "react";
import { getHelpContent, updateHelpContent } from "../api";
import type { User } from "../types";

type Props = {
  user: User | null;
};

export function HelpView({ user }: Props) {
  const isAdmin = user?.role === "admin";
  const [content, setContent] = useState("");
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadHelp = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getHelpContent();
      setContent(response.content);
      setDraft(response.content);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load help content");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHelp();
  }, [loadHelp]);

  async function handleSave(): Promise<void> {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const response = await updateHelpContent(draft);
      setContent(response.content);
      setDraft(response.content);
      setEditing(false);
      setMessage("Help content saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save help content");
    } finally {
      setSaving(false);
    }
  }

  function handleCancelEdit(): void {
    setDraft(content);
    setEditing(false);
    setMessage(null);
  }

  const dirty = draft !== content;

  return (
    <>
      <h2 className="mb-2 text-xl font-semibold text-slate-900 dark:text-white">User instructions</h2>
      <p className="mb-6 text-slate-600 dark:text-slate-400">
        This page explains all app features, including grouped multilingual snippets,
        document upload, and structured JSON import/export workflows. Admins can edit
        the HTML content shown below.
      </p>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200" role="alert">
          {error}
        </div>
      )}
      {message && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-200">
          {message}
        </div>
      )}

      {isAdmin && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {!editing ? (
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600"
            >
              Edit help content
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || !dirty}
                className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 dark:bg-indigo-500 dark:hover:bg-indigo-600"
              >
                {saving ? "Saving..." : "Save"}
              </button>
              <button
                type="button"
                onClick={handleCancelEdit}
                disabled={saving}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
              >
                Cancel
              </button>
            </>
          )}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-8">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent dark:border-indigo-400 dark:border-t-transparent" />
        </div>
      ) : editing && isAdmin ? (
        <div className="space-y-2">
          <label htmlFor="help-html-editor" className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Help HTML
          </label>
          <textarea
            id="help-html-editor"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={20}
            className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 font-mono text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:focus:border-indigo-400 dark:focus:ring-indigo-400/20"
          />
        </div>
      ) : (
        <iframe
          title="App help content"
          srcDoc={content}
          sandbox=""
          className="h-[75vh] w-full rounded-lg border border-slate-200 bg-white dark:border-slate-700"
        />
      )}
    </>
  );
}
