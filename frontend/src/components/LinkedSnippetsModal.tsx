import { useEffect, useState } from "react";
import { getLinkedSnippets } from "../api";
import type { SnippetItem } from "../types";
import { languageInfo } from "./SourceCard";

type Props = {
  snippetId: string;
  onClose: () => void;
};

export function LinkedSnippetsModal({ snippetId, onClose }: Props) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [snippets, setSnippets] = useState<SnippetItem[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    setLoading(true);
    setError(null);
    getLinkedSnippets(snippetId)
      .then((res) => {
        setSnippets(res.snippets);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load translations");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [snippetId]);

  function toggleExpanded(id: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  // Sort snippets by language (de, en, fr, it)
  const sortedSnippets = [...snippets].sort((a, b) => {
    const langOrder = ["de", "en", "fr", "it"];
    const aLang = (a.metadata?.language as string) || "";
    const bLang = (b.metadata?.language as string) || "";
    const aIdx = langOrder.indexOf(aLang.toLowerCase());
    const bIdx = langOrder.indexOf(bLang.toLowerCase());
    return (aIdx === -1 ? 99 : aIdx) - (bIdx === -1 ? 99 : bIdx);
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-xl bg-white shadow-xl dark:bg-slate-800">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            All Language Versions
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-700 dark:hover:text-slate-300"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="max-h-[calc(90vh-8rem)] overflow-y-auto p-6">
          {loading && (
            <div className="flex justify-center py-8">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent dark:border-indigo-400 dark:border-t-transparent" />
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200">
              {error}
            </div>
          )}

          {!loading && !error && snippets.length === 0 && (
            <p className="text-center text-slate-500 dark:text-slate-400">
              No linked translations found.
            </p>
          )}

          {!loading && !error && sortedSnippets.length > 0 && (
            <div className="space-y-4">
              {sortedSnippets.map((snippet) => {
                const lang = (snippet.metadata?.language as string) || "";
                const info = languageInfo(lang);
                const isExpanded = expandedIds.has(snippet.id);
                const text = snippet.text || "";
                const isLong = text.length > 300;
                const displayText = isExpanded || !isLong ? text : text.slice(0, 300) + "...";

                return (
                  <div
                    key={snippet.id}
                    className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/50"
                  >
                    <div className="mb-2 flex items-center gap-2">
                      {info && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-1 text-sm font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                          <span className="font-bold">{info.flag}</span>
                          {info.name}
                        </span>
                      )}
                      {snippet.title && (
                        <span className="text-sm text-slate-500 dark:text-slate-400">
                          {snippet.title}
                        </span>
                      )}
                    </div>
                    <p className="whitespace-pre-wrap text-slate-700 dark:text-slate-300">
                      {displayText}
                    </p>
                    {isLong && (
                      <button
                        type="button"
                        onClick={() => toggleExpanded(snippet.id)}
                        className="mt-2 text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                      >
                        {isExpanded ? "Show less" : "Show more"}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-slate-200 px-6 py-4 dark:border-slate-700">
          <button
            type="button"
            onClick={onClose}
            className="w-full rounded-lg bg-slate-100 px-4 py-2 font-medium text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
