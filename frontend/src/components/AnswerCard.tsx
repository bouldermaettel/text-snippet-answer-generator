import type { AskResponse } from "../types";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { SourceCard } from "./SourceCard";

type Props = { data: AskResponse };

export function AnswerCard({ data }: Props) {
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
      </section>

      {data.sources.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Sources ({data.sources.length})
          </h2>
          <ul className="grid gap-3 sm:grid-cols-1 lg:grid-cols-2">
            {data.sources.map((s, i) => (
              <li key={s.id}>
                <SourceCard source={s} index={i} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
