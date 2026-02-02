import { useState } from "react";
import type { SourceItem } from "../types";
import { ConfidenceBadge } from "./ConfidenceBadge";

const MAX_PREVIEW = 200;

type Props = { source: SourceItem; index: number };

export function SourceCard({ source, index }: Props) {
  const [expanded, setExpanded] = useState(false);
  const isLong = source.text.length > MAX_PREVIEW;
  const displayText = expanded || !isLong ? source.text : source.text.slice(0, MAX_PREVIEW) + "…";

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800/50 dark:hover:border-slate-600">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Source {index + 1}
          {source.title ? ` · ${source.title}` : ""}
        </span>
        <ConfidenceBadge confidence={source.snippet_confidence} label="Match" />
      </div>
      <p className="whitespace-pre-wrap text-slate-700 dark:text-slate-300">{displayText}</p>
      {isLong && (
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="mt-2 text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </article>
  );
}
