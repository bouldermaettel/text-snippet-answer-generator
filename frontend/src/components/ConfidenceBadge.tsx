type Props = { confidence: number; label?: string };

export function ConfidenceBadge({ confidence, label = "Confidence" }: Props) {
  const pct = Math.round(confidence * 100);
  const level = pct >= 70 ? "high" : pct >= 40 ? "medium" : "low";
  const colors =
    level === "high"
      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
      : level === "medium"
        ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
        : "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-sm font-medium ${colors}`}
      title={`${label}: ${pct}%`}
    >
      <span aria-hidden>{label}:</span>
      <span>{pct}%</span>
    </span>
  );
}
