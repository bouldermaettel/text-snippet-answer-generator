import { useState } from "react";
import type { SnippetItem } from "../types";

export type ScopeMode = "all" | "groups" | "snippets";

type Props = {
  mode: ScopeMode;
  onModeChange: (m: ScopeMode) => void;
  groups: string[];
  selectedGroupNames: string[];
  onToggleGroup: (name: string) => void;
  snippets: SnippetItem[];
  selectedSnippetIds: string[];
  onToggleSnippet: (id: string) => void;
  disabled?: boolean;
};

export function AskScopeSelector({
  mode,
  onModeChange,
  groups,
  selectedGroupNames,
  onToggleGroup,
  snippets,
  selectedSnippetIds,
  onToggleSnippet,
  disabled,
}: Props) {
  const [groupSearch, setGroupSearch] = useState("");
  const [snippetSearch, setSnippetSearch] = useState("");

  const filteredGroups = groups.filter((g) =>
    (g || "(ungrouped)").toLowerCase().includes(groupSearch.toLowerCase())
  );

  const filteredSnippets = snippets.filter(
    (s) =>
      (s.title || "").toLowerCase().includes(snippetSearch.toLowerCase()) ||
      s.text.toLowerCase().includes(snippetSearch.toLowerCase())
  );

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800/50">
      <p className="mb-3 text-sm font-medium text-slate-700 dark:text-slate-300">
        Search in
      </p>
      <div className="flex flex-wrap gap-4">
        <label className="flex items-center gap-2">
          <input
            type="radio"
            name="scope"
            checked={mode === "all"}
            onChange={() => onModeChange("all")}
            disabled={disabled}
            className="h-4 w-4 border-slate-300 text-indigo-600 focus:ring-indigo-500"
          />
          <span className="text-sm text-slate-700 dark:text-slate-300">All snippets</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="radio"
            name="scope"
            checked={mode === "groups"}
            onChange={() => onModeChange("groups")}
            disabled={disabled}
            className="h-4 w-4 border-slate-300 text-indigo-600 focus:ring-indigo-500"
          />
          <span className="text-sm text-slate-700 dark:text-slate-300">Selected groups</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="radio"
            name="scope"
            checked={mode === "snippets"}
            onChange={() => onModeChange("snippets")}
            disabled={disabled}
            className="h-4 w-4 border-slate-300 text-indigo-600 focus:ring-indigo-500"
          />
          <span className="text-sm text-slate-700 dark:text-slate-300">Selected snippets</span>
        </label>
      </div>
      {mode === "groups" && groups.length > 0 && (
        <div className="mt-3">
          <input
            type="text"
            placeholder="Search groups..."
            value={groupSearch}
            onChange={(e) => setGroupSearch(e.target.value)}
            disabled={disabled}
            className="mb-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-700 dark:placeholder-slate-500 dark:text-white"
          />
          {filteredGroups.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {filteredGroups.map((g) => (
                <label
                  key={g || "(ungrouped)"}
                  className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
                >
                  <input
                    type="checkbox"
                    checked={selectedGroupNames.includes(g)}
                    onChange={() => onToggleGroup(g)}
                    disabled={disabled}
                    className="h-3.5 w-3.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>{g || "(ungrouped)"}</span>
                </label>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">No groups found</p>
          )}
        </div>
      )}
      {mode === "snippets" && snippets.length > 0 && (
        <div className="mt-3">
          <input
            type="text"
            placeholder="Search snippets..."
            value={snippetSearch}
            onChange={(e) => setSnippetSearch(e.target.value)}
            disabled={disabled}
            className="mb-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-700 dark:placeholder-slate-500 dark:text-white"
          />
          {filteredSnippets.length > 0 ? (
            <div className="max-h-40 overflow-y-auto rounded-lg border border-slate-200 p-2 dark:border-slate-600">
              <ul className="space-y-1">
                {filteredSnippets.map((s) => (
                  <li key={s.id}>
                    <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-700/50">
                      <input
                        type="checkbox"
                        checked={selectedSnippetIds.includes(s.id)}
                        onChange={() => onToggleSnippet(s.id)}
                        disabled={disabled}
                        className="h-3.5 w-3.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="truncate text-slate-700 dark:text-slate-300">
                        {s.title || "(no title)"}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">No snippets found</p>
          )}
        </div>
      )}
    </div>
  );
}
