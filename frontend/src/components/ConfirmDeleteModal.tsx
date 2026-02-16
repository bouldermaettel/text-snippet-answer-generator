import type { SnippetItem } from "../types";

type Props = { snippet: SnippetItem; onConfirm: () => void; onCancel: () => void; loading?: boolean };

export function ConfirmDeleteModal({ snippet, onConfirm, onCancel, loading }: Props) {
  const preview = snippet.text.slice(0, 120) + (snippet.text.length > 120 ? "…" : "");

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4"
      onClick={(e) => e.target === e.currentTarget && onCancel()}
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-snippet-modal-title"
    >
      <div
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4">
          <h2 id="delete-snippet-modal-title" className="text-lg font-semibold text-slate-900 dark:text-white">
            Delete snippet?
          </h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            This cannot be undone. Snippet {snippet.title ? `"${snippet.title}"` : "(no title)"} will be removed.
          </p>
          <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600 dark:border-slate-600 dark:bg-slate-800/50 dark:text-slate-400">
            {preview}
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-200 px-6 py-4 dark:border-slate-700">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 dark:bg-red-700 dark:hover:bg-red-800"
          >
            {loading ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}
