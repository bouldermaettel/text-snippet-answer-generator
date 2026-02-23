import { useState } from "react";
import { updateSnippetGroup } from "../api";
import type { SnippetGroup, SnippetMetadata, TranslationEntry } from "../types";
import { GroupSelector } from "./GroupSelector";

const LANGUAGES = [
  { code: "de", label: "German (DE)" },
  { code: "en", label: "English (EN)" },
  { code: "fr", label: "French (FR)" },
  { code: "it", label: "Italian (IT)" },
];

type Props = {
  snippet: SnippetGroup;
  groups: string[];
  onSaved: () => void;
  onCancel: () => void;
};

export function GroupEditModal({ snippet, groups, onSaved, onCancel }: Props) {
  const [title, setTitle] = useState(snippet.title ?? "");
  const [group, setGroup] = useState(snippet.group ?? "");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [heading, setHeading] = useState((snippet.metadata?.heading as string) ?? "");
  const [category, setCategory] = useState((snippet.metadata?.category as string) ?? "");
  const [instructions, setInstructions] = useState(
    (snippet.metadata?.instructions as string) ?? ""
  );
  const [prerequisites, setPrerequisites] = useState(
    (snippet.metadata?.prerequisites as string) ?? ""
  );

  const existingLangs = Object.keys(snippet.translations);
  const availableLangs = LANGUAGES.filter((l) => existingLangs.includes(l.code));
  const initialTab = availableLangs[0]?.code ?? existingLangs[0] ?? "de";
  const [activeTab, setActiveTab] = useState(initialTab);

  type LangState = { text: string; exampleQuestions: string; isGenerated: boolean };
  const [langStates, setLangStates] = useState<Record<string, LangState>>(() => {
    const s: Record<string, LangState> = {};
    for (const [lang, tr] of Object.entries(snippet.translations)) {
      s[lang] = {
        text: tr.text,
        exampleQuestions: (tr.example_questions ?? []).join("\n"),
        isGenerated: tr.is_generated_translation,
      };
    }
    return s;
  });

  function updateLangState(lang: string, partial: Partial<LangState>) {
    setLangStates((prev) => ({
      ...prev,
      [lang]: { ...prev[lang], ...partial },
    }));
  }

  function buildMetadata(): SnippetMetadata {
    const meta: Record<string, unknown> = {};
    if (heading.trim()) meta.heading = heading.trim();
    if (category.trim()) meta.category = category.trim();
    if (instructions.trim()) meta.instructions = instructions.trim();
    if (prerequisites.trim()) meta.prerequisites = prerequisites.trim();
    return Object.keys(meta).length > 0 ? meta : null;
  }

  function buildTranslations(): Record<string, TranslationEntry> {
    const out: Record<string, TranslationEntry> = {};
    for (const [lang, state] of Object.entries(langStates)) {
      if (!state.text.trim()) continue;
      out[lang] = {
        text: state.text.trim(),
        example_questions: state.exampleQuestions
          .split("\n")
          .map((q) => q.trim())
          .filter((q) => q.length > 0),
        is_generated_translation: state.isGenerated,
      };
    }
    return out;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const translations = buildTranslations();
    if (Object.keys(translations).length === 0) return;

    setMessage(null);
    setLoading(true);
    try {
      await updateSnippetGroup(
        snippet.id,
        title.trim() || undefined,
        group.trim() || null,
        buildMetadata(),
        translations,
      );
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

  const allTabs = LANGUAGES.filter((l) => langStates[l.code]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-900/60 p-4"
      onClick={(e) => e.target === e.currentTarget && onCancel()}
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-group-modal-title"
    >
      <div
        className="my-8 w-full max-w-2xl rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-700">
          <h2 id="edit-group-modal-title" className="text-lg font-semibold text-slate-900 dark:text-white">
            Edit snippet group
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
          {/* Shared fields */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="edit-group-title" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Title
              </label>
              <input
                id="edit-group-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. refund-policy"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
              />
            </div>
            <div>
              <label htmlFor="edit-group-group" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Group
              </label>
              <GroupSelector
                id="edit-group-group"
                groups={groups}
                value={group}
                onChange={setGroup}
                placeholder="e.g. Policies"
              />
            </div>
          </div>

          {/* Advanced shared metadata */}
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
            Shared metadata
          </button>

          {showAdvanced && (
            <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/50">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="edit-group-heading" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Heading
                  </label>
                  <input
                    id="edit-group-heading"
                    type="text"
                    value={heading}
                    onChange={(e) => setHeading(e.target.value)}
                    placeholder="e.g. Customer Support"
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                  />
                </div>
                <div>
                  <label htmlFor="edit-group-category" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Category
                  </label>
                  <input
                    id="edit-group-category"
                    type="text"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    placeholder="e.g. General"
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                  />
                </div>
              </div>
              <div>
                <label htmlFor="edit-group-instructions" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Instructions / Procedure
                </label>
                <textarea
                  id="edit-group-instructions"
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="Internal procedure or instructions for staff..."
                  rows={2}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                />
              </div>
              <div>
                <label htmlFor="edit-group-prerequisites" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Prerequisites
                </label>
                <textarea
                  id="edit-group-prerequisites"
                  value={prerequisites}
                  onChange={(e) => setPrerequisites(e.target.value)}
                  placeholder="Triggering questions, scenarios or conditions..."
                  rows={2}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                />
              </div>
            </div>
          )}

          {/* Language tabs */}
          <div>
            <div className="flex border-b border-slate-200 dark:border-slate-700">
              {allTabs.map((lang) => {
                const state = langStates[lang.code];
                return (
                  <button
                    key={lang.code}
                    type="button"
                    onClick={() => setActiveTab(lang.code)}
                    className={`relative px-4 py-2 text-sm font-medium transition ${
                      activeTab === lang.code
                        ? "text-indigo-600 dark:text-indigo-400"
                        : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
                    }`}
                  >
                    {lang.label}
                    {state?.isGenerated && (
                      <span className="ml-1 text-xs text-amber-500">*</span>
                    )}
                    {activeTab === lang.code && (
                      <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-600 dark:bg-indigo-400" />
                    )}
                  </button>
                );
              })}
            </div>

            {allTabs.map((lang) => {
              if (lang.code !== activeTab) return null;
              const state = langStates[lang.code];
              if (!state) return null;

              return (
                <div key={lang.code} className="space-y-3 pt-3">
                  {state.isGenerated && (
                    <div className="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-900/20 dark:text-amber-300">
                      <svg className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Auto-translated version
                    </div>
                  )}
                  <div>
                    <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                      Text ({lang.label})
                    </label>
                    <textarea
                      value={state.text}
                      onChange={(e) => updateLangState(lang.code, { text: e.target.value })}
                      rows={6}
                      className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                      Example questions ({lang.label})
                    </label>
                    <textarea
                      value={state.exampleQuestions}
                      onChange={(e) => updateLangState(lang.code, { exampleQuestions: e.target.value })}
                      placeholder="One question per line..."
                      rows={2}
                      className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                    />
                  </div>
                </div>
              );
            })}
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
              disabled={loading}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 dark:bg-indigo-500 dark:hover:bg-indigo-600"
            >
              {loading ? "Saving..." : "Save all"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
