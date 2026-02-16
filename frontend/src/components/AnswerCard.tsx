import { useState } from "react";
import type { AskResponse, SourceItem } from "../types";
import { AnswerRefinement } from "./AnswerRefinement";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { LinkedSnippetsModal } from "./LinkedSnippetsModal";
import { SourceCard } from "./SourceCard";

type Props = {
  data: AskResponse;
  selectedSourceIds: string[];
  onToggleSource: (id: string) => void;
  onRefine: (prompt: string) => void;
  refining: boolean;
  onEditSource?: (source: SourceItem) => void;
};

export function AnswerCard({ data, selectedSourceIds, onToggleSource, onRefine, refining, onEditSource }: Props) {
  const selectedCount = selectedSourceIds.length;
  const [linkedSnippetId, setLinkedSnippetId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800/50">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Answer
          </h2>
          <ConfidenceBadge confidence={data.answer_confidence} label="Answer confidence" />
        </div>
        <p className="whitespace-pre-wrap text-slate-800 dark:text-slate-200">{data.answer}</p>

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
