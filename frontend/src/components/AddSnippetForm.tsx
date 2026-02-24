import { useState } from "react";
import { addGroupedSnippet } from "../api";
import type { SnippetMetadata, TranslationEntry } from "../types";
import { GroupSelector } from "./GroupSelector";

const LANGUAGES = [
  { code: "de", label: "German (DE)" },
  { code: "en", label: "English (EN)" },
  { code: "fr", label: "French (FR)" },
  { code: "it", label: "Italian (IT)" },
];

type Props = { onAdded?: () => void; defaultGroup?: string; groups: string[] };

export function AddSnippetForm({ onAdded, defaultGroup, groups }: Props) {
  const [title, setTitle] = useState("");
  const [group, setGroup] = useState(defaultGroup ?? "");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [activeTab, setActiveTab] = useState("de");

  const [heading, setHeading] = useState("");
  const [category, setCategory] = useState("");
  const [instructions, setInstructions] = useState("");
  const [prerequisites, setPrerequisites] = useState("");

  type LangState = { text: string; exampleQuestions: string };
  const [langStates, setLangStates] = useState<Record<string, LangState>>(() => {
    const s: Record<string, LangState> = {};
    for (const lang of LANGUAGES) {
      s[lang.code] = { text: "", exampleQuestions: "" };
    }
    return s;
  });

  function updateLangState(lang: string, partial: Partial<LangState>) {
    setLangStates((prev) => ({
      ...prev,
      [lang]: { ...prev[lang], ...partial },
    }));
  }

  function hasAnyText(): boolean {
    return LANGUAGES.some((l) => langStates[l.code].text.trim().length > 0);
  }

  function filledLangCount(): number {
    return LANGUAGES.filter((l) => langStates[l.code].text.trim().length > 0).length;
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
    for (const lang of LANGUAGES) {
      const state = langStates[lang.code];
      if (!state.text.trim()) continue;
      out[lang.code] = {
        text: state.text.trim(),
        example_questions: state.exampleQuestions
          .split("\n")
          .map((q) => q.trim())
          .filter((q) => q.length > 0),
        is_generated_translation: false,
      };
    }
    return out;
  }

  function resetForm() {
    setTitle("");
    setGroup(defaultGroup ?? "");
    setHeading("");
    setCategory("");
    setInstructions("");
    setPrerequisites("");
    const s: Record<string, LangState> = {};
    for (const lang of LANGUAGES) {
      s[lang.code] = { text: "", exampleQuestions: "" };
    }
    setLangStates(s);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!hasAnyText()) return;

    setMessage(null);
    setLoading(true);
    try {
      const result = await addGroupedSnippet(
        title.trim(),
        group.trim() || null,
        buildMetadata(),
        buildTranslations(),
      );
      const langCount = result.languages.length;
      setMessage({
        type: "ok",
        text: `Snippet added with ${langCount} language${langCount !== 1 ? "s" : ""}.`,
      });
      resetForm();
      onAdded?.();
    } catch (err) {
      setMessage({
        type: "err",
        text: err instanceof Error ? err.message : "Failed to add snippet.",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {/* Title + Group */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="snippet-title" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
            Title
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
          <label htmlFor="snippet-group" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
            Group
          </label>
          <GroupSelector
            id="snippet-group"
            groups={groups}
            value={group}
            onChange={setGroup}
            placeholder="e.g. Policies"
          />
        </div>
      </div>

      {/* Shared metadata */}
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
              <label htmlFor="snippet-heading" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Heading
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
                Category
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
            <label htmlFor="snippet-instructions" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Instructions / Procedure
            </label>
            <textarea
              id="snippet-instructions"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Internal procedure or instructions for staff..."
              rows={2}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            />
          </div>
          <div>
            <label htmlFor="snippet-prerequisites" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Prerequisites
            </label>
            <textarea
              id="snippet-prerequisites"
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
          {LANGUAGES.map((lang) => {
            const filled = langStates[lang.code].text.trim().length > 0;
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
                {filled && (
                  <span className="ml-1 text-xs text-emerald-500">&#10003;</span>
                )}
                {activeTab === lang.code && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-600 dark:bg-indigo-400" />
                )}
              </button>
            );
          })}
        </div>

        {LANGUAGES.map((lang) => {
          if (lang.code !== activeTab) return null;
          const state = langStates[lang.code];
          return (
            <div key={lang.code} className="space-y-3 pt-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Text ({lang.label})
                </label>
                <textarea
                  value={state.text}
                  onChange={(e) => updateLangState(lang.code, { text: e.target.value })}
                  placeholder={`Paste or type the text in ${lang.label}…`}
                  rows={5}
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

      {/* Footer */}
      <div className="flex items-center justify-between border-t border-slate-200 pt-3 dark:border-slate-700">
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {filledLangCount() === 0
            ? "Fill in at least one language"
            : `${filledLangCount()} language${filledLangCount() !== 1 ? "s" : ""} filled`}
        </p>
        <button
          type="submit"
          disabled={loading || !hasAnyText()}
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
