import { useState } from "react";
import type { User } from "../types";
import type { Theme } from "./ThemeToggle";
import { ThemeToggle } from "./ThemeToggle";

type Tab = "ask" | "collection" | "users";

type Props = {
  tab: Tab;
  onTabChange: (t: Tab) => void;
  groups: string[];
  selectedGroups: string[];
  onToggleGroup: (g: string) => void;
  onClearGroups: () => void;
  backendUnavailable: boolean;
  theme: Theme;
  onThemeChange: (t: Theme) => void;
  user: User | null;
  onLogout: () => void;
};

export function Sidebar({
  tab,
  onTabChange,
  groups,
  selectedGroups,
  onToggleGroup,
  onClearGroups,
  backendUnavailable,
  theme,
  onThemeChange,
  user,
  onLogout,
}: Props) {
  const [groupSearch, setGroupSearch] = useState("");

  const filteredGroups = groups.filter((g) =>
    (g || "(ungrouped)").toLowerCase().includes(groupSearch.toLowerCase())
  );

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800/50">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-4 dark:border-slate-700">
        <h1 className="text-lg font-semibold text-slate-900 dark:text-white">
          Snippet Answer Generator
        </h1>
        <ThemeToggle theme={theme} onThemeChange={onThemeChange} />
      </div>
      <nav className="flex flex-col gap-0.5 p-2">
        <button
          type="button"
          onClick={() => onTabChange("ask")}
          className={`flex items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors ${
            tab === "ask"
              ? "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200"
              : "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700/50"
          }`}
        >
          <svg className="h-5 w-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Ask
        </button>
        <button
          type="button"
          onClick={() => onTabChange("collection")}
          className={`flex items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors ${
            tab === "collection"
              ? "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200"
              : "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700/50"
          }`}
        >
          <svg className="h-5 w-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          Collection
        </button>
        {user?.role === "admin" && (
          <button
            type="button"
            onClick={() => onTabChange("users")}
            className={`flex items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors ${
              tab === "users"
                ? "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200"
                : "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700/50"
            }`}
          >
            <svg className="h-5 w-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
            Users
          </button>
        )}
      </nav>
      {tab === "collection" && !backendUnavailable && (
        <div className="border-t border-slate-200 p-3 dark:border-slate-700">
          <p className="mb-2 px-2 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Groups
          </p>
          <input
            type="text"
            placeholder="Search groups..."
            value={groupSearch}
            onChange={(e) => setGroupSearch(e.target.value)}
            className="mb-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-700 dark:placeholder-slate-500 dark:text-white"
          />
          <button
            type="button"
            onClick={onClearGroups}
            className={`mb-1 w-full rounded-lg px-3 py-2 text-left text-sm ${
              selectedGroups.length === 0
                ? "bg-slate-200 font-medium text-slate-900 dark:bg-slate-600 dark:text-white"
                : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700/50"
            }`}
          >
            All
          </button>
          {filteredGroups.length > 0 ? (
            filteredGroups.map((g) => (
              <button
                key={g || "(ungrouped)"}
                type="button"
                onClick={() => onToggleGroup(g)}
                className={`mb-1 w-full rounded-lg px-3 py-2 text-left text-sm ${
                  selectedGroups.includes(g)
                    ? "bg-slate-200 font-medium text-slate-900 dark:bg-slate-600 dark:text-white"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700/50"
                }`}
              >
                <span className="inline-flex items-center gap-2">
                  <span
                    className={`inline-block h-4 w-4 shrink-0 rounded border ${
                      selectedGroups.includes(g)
                        ? "border-slate-600 bg-slate-600 dark:border-slate-400 dark:bg-slate-400"
                        : "border-slate-400 dark:border-slate-500"
                    }`}
                    aria-hidden
                  >
                    {selectedGroups.includes(g) && (
                      <svg className="h-full w-full p-0.5 text-white dark:text-slate-800" fill="currentColor" viewBox="0 0 12 12">
                        <path d="M10.28 2.28L3.989 8.575 1.695 6.28A1 1 0 00.28 7.695l3 3a1 1 0 001.414 0l7-7A1 1 0 0010.28 2.28z" />
                      </svg>
                    )}
                  </span>
                  {g || "(ungrouped)"}
                </span>
              </button>
            ))
          ) : (
            <p className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400">No groups found</p>
          )}
        </div>
      )}
      <div className="mt-auto border-t border-slate-200 p-2 dark:border-slate-700">
        {user && (
          <p className="truncate px-3 py-2 text-xs text-slate-500 dark:text-slate-400" title={user.email}>
            {user.email}
          </p>
        )}
        <button
          type="button"
          onClick={onLogout}
          className="w-full rounded-lg px-3 py-2 text-left text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700/50"
        >
          Log out
        </button>
      </div>
    </aside>
  );
}
