import { useCallback, useEffect, useState } from "react";
import {
  backendUnreachableMessage,
  deleteSnippet,
  getSnippets,
  isNetworkError,
  openDocumentInNewTab,
  updateSnippet,
} from "../api";
import type { SnippetItem } from "../types";
import { AddSnippetModal } from "./AddSnippetModal";
import { ConfirmDeleteModal } from "./ConfirmDeleteModal";
import { EditSnippetModal } from "./EditSnippetModal";
import { GroupSelector } from "./GroupSelector";

type Props = {
  selectedGroups?: string[];
  onGroupsChange?: () => void;
  groups?: string[];
};

const LANGUAGES = [
  { code: "de", label: "DE", name: "German" },
  { code: "en", label: "EN", name: "English" },
  { code: "fr", label: "FR", name: "French" },
  { code: "it", label: "IT", name: "Italian" },
];

export function CollectionView({ selectedGroups = [], onGroupsChange, groups = [] }: Props) {
  const [snippets, setSnippets] = useState<SnippetItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [snippetToDelete, setSnippetToDelete] = useState<SnippetItem | null>(null);
  const [snippetToEdit, setSnippetToEdit] = useState<SnippetItem | null>(null);
  const [editingGroupSnippetId, setEditingGroupSnippetId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  
  // Filter state
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>([]);
  const [showTranslations, setShowTranslations] = useState(false);
  const [snippetSearch, setSnippetSearch] = useState("");

  // Client-side filtering for search
  const filteredSnippets = snippets.filter(
    (s) =>
      !snippetSearch ||
      (s.title || "").toLowerCase().includes(snippetSearch.toLowerCase()) ||
      s.text.toLowerCase().includes(snippetSearch.toLowerCase())
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getSnippets(
        500,
        0,
        selectedGroups.length ? selectedGroups : undefined,
        selectedLanguages.length ? selectedLanguages : undefined,
        showTranslations
      );
      setSnippets(res.snippets);
      setTotal(res.total);
    } catch (e) {
      setError(
        isNetworkError(e) ? backendUnreachableMessage() : (e instanceof Error ? e.message : "Failed to load snippets")
      );
    } finally {
      setLoading(false);
    }
  }, [selectedGroups, selectedLanguages, showTranslations]);

  const toggleLanguage = (code: string) => {
    setSelectedLanguages((prev) =>
      prev.includes(code) ? prev.filter((l) => l !== code) : [...prev, code]
    );
  };

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onAddedOrSaved = useCallback(() => {
    refresh();
    onGroupsChange?.();
  }, [refresh, onGroupsChange]);

  async function handleDelete() {
    if (!snippetToDelete) return;
    setDeleting(true);
    try {
      await deleteSnippet(snippetToDelete.id);
      setSnippetToDelete(null);
      await refresh();
      onGroupsChange?.();
    } catch (e) {
      setError(
        isNetworkError(e) ? backendUnreachableMessage() : (e instanceof Error ? e.message : "Failed to delete")
      );
    } finally {
      setDeleting(false);
    }
  }

  const handleAdded = () => {
    setShowAddModal(false);
    onAddedOrSaved();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <p className="text-slate-600 dark:text-slate-400">
          {snippetSearch ? `${filteredSnippets.length} of ${total}` : total} snippet{(snippetSearch ? filteredSnippets.length : total) !== 1 ? "s" : ""}
          {selectedGroups.length > 0
            ? ` in ${selectedGroups.length === 1
                ? `"${selectedGroups[0] || "(ungrouped)"}"`
                : `${selectedGroups.length} groups`}`
            : " in your collection"}
          {selectedLanguages.length > 0 && ` (${selectedLanguages.map(l => l.toUpperCase()).join(", ")})`}
          {showTranslations && " + translations"}
          {snippetSearch && ` matching "${snippetSearch}"`}
        </p>
        <button
          type="button"
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add snippet
        </button>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/50">
        <input
          type="text"
          placeholder="Search snippets..."
          value={snippetSearch}
          onChange={(e) => setSnippetSearch(e.target.value)}
          className="w-48 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-700 dark:placeholder-slate-500 dark:text-white"
        />
        
        <div className="h-6 w-px bg-slate-300 dark:bg-slate-600" />
        
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-600 dark:text-slate-400">Language:</span>
          <div className="flex gap-1">
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                type="button"
                onClick={() => toggleLanguage(lang.code)}
                title={lang.name}
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                  selectedLanguages.includes(lang.code)
                    ? "bg-blue-600 text-white"
                    : "bg-white text-slate-600 hover:bg-slate-100 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
                }`}
              >
                {lang.label}
              </button>
            ))}
            {selectedLanguages.length > 0 && (
              <button
                type="button"
                onClick={() => setSelectedLanguages([])}
                className="ml-1 rounded-md px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700"
              >
                Clear
              </button>
            )}
          </div>
        </div>
        
        <div className="h-6 w-px bg-slate-300 dark:bg-slate-600" />
        
        <label className="flex cursor-pointer items-center gap-2">
          <input
            type="checkbox"
            checked={showTranslations}
            onChange={(e) => setShowTranslations(e.target.checked)}
            className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-700"
          />
          <span className="text-sm text-slate-600 dark:text-slate-400">
            Show generated translations
          </span>
        </label>
      </div>

      {error && (
        <div
          className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200"
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

      {!loading && snippets.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center dark:border-slate-700 dark:bg-slate-800/50">
          <p className="text-slate-500 dark:text-slate-400">No snippets yet. Add one or upload documents.</p>
          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            className="mt-4 text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
          >
            Add snippet
          </button>
        </div>
      )}

      {!loading && snippets.length > 0 && filteredSnippets.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center dark:border-slate-700 dark:bg-slate-800/50">
          <p className="text-slate-500 dark:text-slate-400">No snippets found matching "{snippetSearch}"</p>
          <button
            type="button"
            onClick={() => setSnippetSearch("")}
            className="mt-4 text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
          >
            Clear search
          </button>
        </div>
      )}

      {!loading && filteredSnippets.length > 0 && (
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filteredSnippets.map((s) => {
            const lang = s.metadata?.language as string | undefined;
            const heading = s.metadata?.heading as string | undefined;
            const linkedSnippets = s.metadata?.linked_snippets as string[] | undefined;
            const hasGeneratedTranslations = s.metadata?.has_generated_translations as boolean | undefined;
            const isGeneratedTranslation = s.metadata?.is_generated_translation as boolean | undefined;
            const langFlags: Record<string, string> = { de: "DE", fr: "FR", it: "IT", en: "EN" };
            
            return (
              <li
                key={s.id}
                className={`flex min-h-[140px] flex-col rounded-xl border p-4 ${
                  isGeneratedTranslation
                    ? "border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-900/20"
                    : "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800/50"
                }`}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-slate-900 dark:text-white">
                      {s.title || "(no title)"}
                    </p>
                    {isGeneratedTranslation && (
                      <span className="shrink-0 rounded-full bg-amber-200 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-800 dark:text-amber-200">
                        Auto
                      </span>
                    )}
                  </div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-1">
                    {editingGroupSnippetId === s.id ? (
                      <div className="w-32">
                        <GroupSelector
                          id={`group-${s.id}`}
                          groups={groups}
                          value={s.group ?? ""}
                          onChange={() => {}}
                          onSelect={async (newGroup) => {
                            try {
                              await updateSnippet(
                                s.id,
                                s.text,
                                s.title ?? undefined,
                                newGroup.trim() || null,
                                s.metadata
                              );
                              setEditingGroupSnippetId(null);
                              await refresh();
                              onGroupsChange?.();
                            } catch (e) {
                              setError(
                                isNetworkError(e)
                                  ? backendUnreachableMessage()
                                  : e instanceof Error
                                    ? e.message
                                    : "Failed to update group"
                              );
                            }
                          }}
                          onClose={() => setEditingGroupSnippetId(null)}
                          placeholder="Group"
                        />
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setEditingGroupSnippetId(s.id)}
                        className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
                      >
                        {s.group != null && s.group !== "" ? s.group : "(ungrouped)"}
                      </button>
                    )}
                    {heading && (
                      <span className="inline-flex rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                        {heading}
                      </span>
                    )}
                    {/* Show primary language */}
                    {lang && (
                      <span className="inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                        {langFlags[lang.toLowerCase()] ?? lang.toUpperCase()}
                      </span>
                    )}
                    {/* Show auto-translated indicator */}
                    {hasGeneratedTranslations && (
                      <span className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-300" title="Has auto-translated versions">
                        Auto
                      </span>
                    )}
                  </div>
                  {/* Show linked snippets info */}
                  {linkedSnippets && linkedSnippets.length > 0 && (
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      Linked: {linkedSnippets.slice(0, 3).join(", ")}{linkedSnippets.length > 3 ? ` +${linkedSnippets.length - 3} more` : ""}
                    </p>
                  )}
                  <p className="mt-1 line-clamp-2 text-sm text-slate-600 dark:text-slate-400">
                    {s.text}
                  </p>
                  {s.metadata?.source_document_url && (
                    <button
                      type="button"
                      onClick={() => openDocumentInNewTab(s.id).catch((e) => alert(e instanceof Error ? e.message : "Failed to open document"))}
                      className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                    >
                      View original document
                      <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </button>
                  )}
                </div>
                <div className="mt-3 flex shrink-0 justify-end gap-1">
                  <button
                    type="button"
                    onClick={() => setSnippetToEdit(s)}
                    className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-300"
                    aria-label={`Edit ${s.title || "snippet"}`}
                  >
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() => setSnippetToDelete(s)}
                    className="rounded-lg p-2 text-slate-500 hover:bg-red-50 hover:text-red-600 dark:hover:bg-slate-700 dark:hover:text-red-400"
                    aria-label={`Delete ${s.title || "snippet"}`}
                  >
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {showAddModal && (
        <AddSnippetModal
          onClose={() => setShowAddModal(false)}
          onAdded={handleAdded}
          defaultGroup={selectedGroups[0] ?? undefined}
          groups={groups}
        />
      )}

      {snippetToDelete && (
        <ConfirmDeleteModal
          snippet={snippetToDelete}
          onConfirm={handleDelete}
          onCancel={() => setSnippetToDelete(null)}
          loading={deleting}
        />
      )}

      {snippetToEdit && (
        <EditSnippetModal
          snippet={snippetToEdit}
          groups={groups}
          onSaved={() => {
            setSnippetToEdit(null);
            onAddedOrSaved();
          }}
          onCancel={() => setSnippetToEdit(null)}
        />
      )}
    </div>
  );
}
