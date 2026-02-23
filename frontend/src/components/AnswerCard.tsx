import { useCallback, useState, type ReactNode } from "react";
import type { AskResponse, SourceItem } from "../types";
import { AnswerRefinement } from "./AnswerRefinement";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { LinkedSnippetsModal } from "./LinkedSnippetsModal";
import { SourceCard } from "./SourceCard";

const URL_RE = /https?:\/\/\S+/g;

function linkifyText(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = URL_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const url = match[0].replace(/[.,;:!?)]+$/, "");
    parts.push(
      <a
        key={match.index}
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-indigo-600 hover:underline dark:text-indigo-400"
      >
        {url}
      </a>,
    );
    lastIndex = match.index + url.length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

type Props = {
  data: AskResponse;
  selectedSourceIds: string[];
  onToggleSource: (id: string) => void;
  onRefine: (prompt: string) => void;
  refining: boolean;
  onEditSource?: (source: SourceItem) => void;
  greeting?: string;
};

export function AnswerCard({ data, selectedSourceIds, onToggleSource, onRefine, refining, onEditSource, greeting }: Props) {
  const selectedCount = selectedSourceIds.length;
  const [linkedSnippetId, setLinkedSnippetId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    const text = greeting?.trim()
      ? `${greeting.trim()}\n\n${data.answer}`
      : data.answer;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [data.answer, greeting]);

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800/50">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Answer
          </h2>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopy}
              title="Antwort in Zwischenablage kopieren"
              className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
            >
              {copied ? (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 text-green-500" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Kopiert
                </>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
                    <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z" />
                  </svg>
                  Kopieren
                </>
              )}
            </button>
            <ConfidenceBadge confidence={data.answer_confidence} label="Answer confidence" />
          </div>
        </div>
        {greeting?.trim() && (
          <p className="mb-2 whitespace-pre-wrap text-slate-800 dark:text-slate-200">{greeting.trim()}</p>
        )}
        <p className="whitespace-pre-wrap text-slate-800 dark:text-slate-200">{linkifyText(data.answer)}</p>

        {/* Refinement input */}
        <AnswerRefinement onRefine={onRefine} loading={refining} />
      </section>

      {data.sources.length > 0 && (
        <section>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Sources ({data.sources.length})
            </h2>
            {selectedCount > 0 && (
              <span className="rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
                {selectedCount} selected for context
              </span>
            )}
          </div>
          <ul className="flex flex-col gap-4">
            {data.sources.map((s, i) => (
              <li key={s.id}>
                <SourceCard
                  source={s}
                  index={i}
                  isSelected={selectedSourceIds.includes(s.id)}
                  onToggleSelect={onToggleSource}
                  showSelectButton
                  onShowAllLanguages={setLinkedSnippetId}
                  onEdit={onEditSource}
                />
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Linked snippets modal */}
      {linkedSnippetId && (
        <LinkedSnippetsModal
          snippetId={linkedSnippetId}
          onClose={() => setLinkedSnippetId(null)}
        />
      )}
    </div>
  );
}
