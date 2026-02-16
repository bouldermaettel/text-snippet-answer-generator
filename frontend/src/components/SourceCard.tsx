import { useState } from "react";
import { openDocumentInNewTab } from "../api";
import type { SourceItem } from "../types";
import { ConfidenceBadge } from "./ConfidenceBadge";

const SHORT_EXCERPT = 120;

/** First sentence or first N chars for a compact source preview. */
function shortExcerpt(text: string, maxLen: number = SHORT_EXCERPT): string {
  const trimmed = text.trim();
  const dot = trimmed.indexOf(". ");
  if (dot >= 0 && dot < maxLen) return trimmed.slice(0, dot + 1);
  if (trimmed.length <= maxLen) return trimmed;
  return trimmed.slice(0, maxLen).trim() + "...";
}

/** Language code to flag emoji and full name. */
export function languageInfo(lang: string): { flag: string; name: string } | null {
  const map: Record<string, { flag: string; name: string }> = {
    de: { flag: "DE", name: "German" },
    fr: { flag: "FR", name: "French" },
    it: { flag: "IT", name: "Italian" },
    en: { flag: "EN", name: "English" },
  };
  return map[lang.toLowerCase()] ?? null;
}

type Props = {
  source: SourceItem;
  index: number;
  isSelected?: boolean;
  onToggleSelect?: (id: string) => void;
  showSelectButton?: boolean;
  onShowAllLanguages?: (snippetId: string) => void;
  onEdit?: (source: SourceItem) => void;
};

export function SourceCard({ source, index, isSelected, onToggleSelect, showSelectButton, onShowAllLanguages, onEdit }: Props) {
  const [expanded, setExpanded] = useState(false);
  const text = source.text ?? "";
  const isLong = text.length > SHORT_EXCERPT;
  const displayText =
    (expanded || !isLong ? text : shortExcerpt(text)) || text || "";

  const meta = source.metadata;
  const language = meta?.language as string | undefined;
  const heading = meta?.heading as string | undefined;
  const category = meta?.category as string | undefined;
  const linkedSnippets = meta?.linked_snippets as string[] | undefined;
  const translationSource = meta?.translation_source as string | undefined;
  const hasGeneratedTranslations = meta?.has_generated_translations as boolean | undefined;
  const availableLanguages = meta?.available_languages as string[] | undefined;
  const langInfo = language ? languageInfo(language) : null;
  const hasTranslations = (linkedSnippets && linkedSnippets.length > 0) || hasGeneratedTranslations;

  return (
    <article className={`rounded-xl border p-4 shadow-sm transition ${
      isSelected
        ? "border-indigo-400 bg-indigo-50 dark:border-indigo-500 dark:bg-indigo-900/20"
        : "border-slate-200 bg-white hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800/50 dark:hover:border-slate-600"
    }`}>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Source {index + 1}
          {source.title && !source.section_label ? ` - ${source.title}` : ""}
          {source.section_label ? ` - ${source.section_label}` : ""}
        </span>
        <div className="flex items-center gap-2">
          {showSelectButton && onToggleSelect && (
            <button
              type="button"
              onClick={() => onToggleSelect(source.id)}
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition ${
                isSelected
                  ? "bg-indigo-600 text-white hover:bg-indigo-700"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
              }`}
            >
              {isSelected ? (
                <>
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Included
                </>
              ) : (
                <>
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Include
                </>
              )}
            </button>
          )}
          <ConfidenceBadge confidence={source.snippet_confidence} label="Match" />
        </div>
      </div>

      {/* Metadata badges */}
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        {langInfo && (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
            <span>{langInfo.flag}</span>
            {langInfo.name}
          </span>
        )}
        {translationSource === "generated" && (
          <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
            Auto-translated
          </span>
        )}
        {heading && (
          <span className="inline-flex items-center rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
            {heading}
          </span>
        )}
        {category && category !== "General" && (
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
            {category}
          </span>
        )}
        {/* Show all languages button */}
        {hasTranslations && onShowAllLanguages && (
          <button
            type="button"
            onClick={() => onShowAllLanguages(source.id)}
            className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700 hover:bg-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:hover:bg-emerald-900/50"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
            </svg>
            All languages ({availableLanguages?.length ?? (linkedSnippets ? linkedSnippets.length + 1 : 1)})
          </button>
        )}
      </div>

      {source.source_document_url && (
        <button
          type="button"
          onClick={() => openDocumentInNewTab(source.id).catch((e) => alert(e instanceof Error ? e.message : "Failed to open document"))}
          className="mb-2 inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
        >
          View in original document
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </button>
      )}
      {source.section_label && (
        <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{source.section_label}</p>
      )}
      <p className="whitespace-pre-wrap text-slate-700 dark:text-slate-300">{displayText}</p>
      <div className="mt-3 flex items-center justify-between">
        <div>
          {isLong && (
            <button
              type="button"
              onClick={() => setExpanded((e) => !e)}
              className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
            >
              {expanded ? "Show less" : "Show more"}
            </button>
          )}
        </div>
        {onEdit && (
          <button
            type="button"
            onClick={() => onEdit(source)}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-300"
            aria-label="Edit snippet"
            title="Edit snippet"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
          </button>
        )}
      </div>
    </article>
  );
}
