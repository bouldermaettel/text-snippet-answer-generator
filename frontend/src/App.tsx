import { useCallback, useEffect, useState } from "react";
import {
  ask,
  backendUnreachableMessage,
  clearToken,
  getGroups,
  getMe,
  getSnippets,
  getToken,
  healthCheck,
  isNetworkError,
  refineAnswer,
  setOnUnauthorized,
} from "./api";
import type { AskResponse, SnippetItem, SourceItem, User } from "./types";
import { AnswerCard } from "./components/AnswerCard";
import { AskScopeSelector, type ScopeMode } from "./components/AskScopeSelector";
import { CollectionView } from "./components/CollectionView";
import { EditSnippetModal } from "./components/EditSnippetModal";
import { LoginRegister } from "./components/LoginRegister";
import { QuestionInput } from "./components/QuestionInput";
import { Sidebar } from "./components/Sidebar";
import type { Theme } from "./components/ThemeToggle";
import { UsersView } from "./components/UsersView";

const THEME_KEY = "theme";

function getStoredTheme(): Theme {
  try {
    const v = localStorage.getItem(THEME_KEY);
    if (v === "light" || v === "dark" || v === "system") return v;
  } catch {
    // ignore
  }
  return "system";
}

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  const dark =
    theme === "dark" ||
    (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  if (dark) root.classList.add("dark");
  else root.classList.remove("dark");
}

type Tab = "ask" | "collection" | "users";

export default function App() {
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const [user, setUser] = useState<User | null>(null);
  const [tab, setTab] = useState<Tab>("ask");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [backendUnavailable, setBackendUnavailable] = useState(false);
  const [groups, setGroups] = useState<string[]>([]);
  const [selectedGroups, setSelectedGroups] = useState<string[]>([]);
  const [scopeMode, setScopeMode] = useState<ScopeMode>("all");
  const [selectedGroupNames, setSelectedGroupNames] = useState<string[]>([]);
  const [selectedSnippetIds, setSelectedSnippetIds] = useState<string[]>([]);
  const [snippetsForScope, setSnippetsForScope] = useState<SnippetItem[]>([]);
  const [answerCloseness, setAnswerCloseness] = useState(0.5);
  const [useHyde, setUseHyde] = useState(false);
  const [useKeywordRerank, setUseKeywordRerank] = useState(true);
  const [theme, setTheme] = useState<Theme>(getStoredTheme);
  const [refining, setRefining] = useState(false);
  const [contextSourceIds, setContextSourceIds] = useState<string[]>([]);
  const [originalQuestion, setOriginalQuestion] = useState("");
  const [questionLanguage, setQuestionLanguage] = useState<string>("");  // empty = all languages
  const [sourceToEdit, setSourceToEdit] = useState<SourceItem | null>(null);

  useEffect(() => {
    setOnUnauthorized(() => setTokenState(null));
    return () => setOnUnauthorized(() => {});
  }, []);

  useEffect(() => {
    if (token) {
      getMe()
        .then(setUser)
        .catch(() => {
          setTokenState(null);
        });
    } else {
      setUser(null);
    }
  }, [token]);

  const refreshGroups = useCallback(async () => {
    try {
      const res = await getGroups();
      setGroups(res.groups);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      // ignore
    }
  }, [theme]);

  useEffect(() => {
    healthCheck().then((ok) => setBackendUnavailable(!ok));
    refreshGroups();
  }, [refreshGroups]);

  useEffect(() => {
    if (theme !== "system") return;
    const m = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = () => applyTheme("system");
    m.addEventListener("change", listener);
    return () => m.removeEventListener("change", listener);
  }, [theme]);

  useEffect(() => {
    if (tab === "collection") {
      healthCheck().then((ok) => setBackendUnavailable(!ok));
      refreshGroups();
    }
  }, [tab, refreshGroups]);

  useEffect(() => {
    if (tab === "ask" && scopeMode === "snippets" && !backendUnavailable) {
      getSnippets(500, 0)
        .then((r) => setSnippetsForScope(r.snippets))
        .catch(() => setSnippetsForScope([]));
    }
  }, [tab, scopeMode, backendUnavailable]);

  async function handleAsk() {
    const q = question.trim();
    if (!q) return;
    setError(null);
    setResult(null);
    setLoading(true);
    setContextSourceIds([]);
    setOriginalQuestion(q);
    try {
      const options: {
        groupNames?: string[];
        snippetIds?: string[];
        languages?: string[];
        answerCloseness?: number;
        useHyde?: boolean;
        useKeywordRerank?: boolean;
      } =
        scopeMode === "groups" && selectedGroupNames.length
          ? { groupNames: selectedGroupNames }
          : scopeMode === "snippets" && selectedSnippetIds.length
            ? { snippetIds: selectedSnippetIds }
            : {};
      options.answerCloseness = answerCloseness;
      options.useHyde = useHyde;
      options.useKeywordRerank = useKeywordRerank;
      // Add language filter if a specific language is selected
      if (questionLanguage) {
        options.languages = [questionLanguage];
      }
      const data = await ask(q, options);
      setResult(data);
    } catch (e) {
      setError(
        isNetworkError(e) ? backendUnreachableMessage() : (e instanceof Error ? e.message : "Request failed")
      );
    } finally {
      setLoading(false);
    }
  }

  function handleToggleGroup(name: string) {
    setSelectedGroupNames((prev) =>
      prev.includes(name) ? prev.filter((g) => g !== name) : [...prev, name]
    );
  }

  function handleCollectionToggleGroup(name: string) {
    setSelectedGroups((prev) =>
      prev.includes(name) ? prev.filter((g) => g !== name) : [...prev, name]
    );
  }

  function handleCollectionClearGroups() {
    setSelectedGroups([]);
  }

  function handleToggleSnippet(id: string) {
    setSelectedSnippetIds((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  }

  function handleToggleContextSource(id: string) {
    setContextSourceIds((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  }

  async function handleRefine(refinementPrompt: string) {
    if (!result) return;
    setRefining(true);
    setError(null);
    try {
      const refined = await refineAnswer({
        originalQuestion,
        originalAnswer: result.answer,
        refinementPrompt,
        selectedSourceIds: contextSourceIds,
        sources: result.sources,
        answerCloseness,
      });
      setResult({
        answer: refined.answer,
        sources: result.sources, // Keep original sources so user can continue selecting
        answer_confidence: refined.answer_confidence,
      });
    } catch (e) {
      setError(
        isNetworkError(e) ? backendUnreachableMessage() : (e instanceof Error ? e.message : "Refinement failed")
      );
    } finally {
      setRefining(false);
    }
  }

  // Convert SourceItem to SnippetItem for edit modal
  function sourceToSnippet(source: SourceItem): SnippetItem {
    return {
      id: source.id,
      text: source.text,
      title: source.title,
      group: (source.metadata?.group as string) ?? null,
      metadata: source.metadata ?? null,
    };
  }

  function handleSourceSaved() {
    setSourceToEdit(null);
    // Optionally re-ask the question to get updated snippet data
    // For now, just close the modal
  }

  if (!token) {
    return (
      <LoginRegister onSuccess={() => setTokenState(getToken())} />
    );
  }

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-900">
      <Sidebar
        tab={tab}
        onTabChange={setTab}
        groups={groups}
        selectedGroups={selectedGroups}
        onToggleGroup={handleCollectionToggleGroup}
        onClearGroups={handleCollectionClearGroups}
        backendUnavailable={backendUnavailable}
        theme={theme}
        onThemeChange={setTheme}
        user={user}
        onLogout={() => {
          clearToken();
          setTokenState(null);
        }}
      />
      <main className="min-w-0 flex-1 overflow-auto">
        <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
          {backendUnavailable && (
            <div
              className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200"
              role="alert"
            >
              <p className="font-medium">Cannot reach the backend.</p>
              <p className="mt-1 text-sm">
                Is the server running on port 8000? Start it with:{" "}
                <code className="rounded bg-amber-100 px-1 dark:bg-amber-900/40">
                  cd backend && uvicorn app.main:app --reload --port 8000
                </code>
              </p>
            </div>
          )}

          {tab === "ask" && (
            <>
              <h2 className="mb-2 text-xl font-semibold text-slate-900 dark:text-white">
                Ask a question
              </h2>
              <p className="mb-6 text-slate-600 dark:text-slate-400">
                Answers are built from your snippet library with sources and confidence.
              </p>

              <div className="mb-6">
                <AskScopeSelector
                  mode={scopeMode}
                  onModeChange={setScopeMode}
                  groups={groups}
                  selectedGroupNames={selectedGroupNames}
                  onToggleGroup={handleToggleGroup}
                  snippets={snippetsForScope}
                  selectedSnippetIds={selectedSnippetIds}
                  onToggleSnippet={handleToggleSnippet}
                  disabled={loading}
                />
              </div>

              <div className="mb-6">
                <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Antwortnähe (0 = frei, 1 = wörtlich)
                </label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.1}
                  value={answerCloseness}
                  onChange={(e) => setAnswerCloseness(Number(e.target.value))}
                  className="h-2 w-full max-w-xs cursor-pointer appearance-none rounded-lg bg-slate-200 dark:bg-slate-600"
                />
                <span className="ml-2 text-sm text-slate-600 dark:text-slate-400">
                  {Math.round(answerCloseness * 100)}%
                </span>
              </div>

              <div className="mb-6 flex flex-wrap items-center gap-6">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="use-hyde"
                    checked={useHyde}
                    onChange={(e) => setUseHyde(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-700"
                  />
                  <label htmlFor="use-hyde" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    Hypothetische Antwort für Suche nutzen (HyDE)
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="use-keyword-rerank"
                    checked={useKeywordRerank}
                    onChange={(e) => setUseKeywordRerank(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-700"
                  />
                  <label htmlFor="use-keyword-rerank" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    Keyword-Reranking
                  </label>
                </div>
              </div>

              <div className="mb-4">
                <QuestionInput
                  value={question}
                  onChange={setQuestion}
                  onSubmit={handleAsk}
                  loading={loading}
                />
              </div>

              {/* Language filter for search */}
              <div className="mb-8 flex items-center gap-3">
                <span className="text-sm font-medium text-slate-600 dark:text-slate-400">Search in:</span>
                <div className="flex gap-1">
                  {[
                    { code: "", label: "All" },
                    { code: "de", label: "DE" },
                    { code: "en", label: "EN" },
                    { code: "fr", label: "FR" },
                    { code: "it", label: "IT" },
                  ].map((lang) => (
                    <button
                      key={lang.code}
                      type="button"
                      onClick={() => setQuestionLanguage(lang.code)}
                      className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                        questionLanguage === lang.code
                          ? "bg-indigo-600 text-white"
                          : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
                      }`}
                    >
                      {lang.label}
                    </button>
                  ))}
                </div>
              </div>

              {error && (
                <div
                  className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200"
                  role="alert"
                >
                  {error}
                </div>
              )}

              {loading && (
                <div className="flex justify-center py-12">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent dark:border-indigo-400 dark:border-t-transparent" />
                </div>
              )}

              {!loading && result && (
                <AnswerCard
                  data={result}
                  selectedSourceIds={contextSourceIds}
                  onToggleSource={handleToggleContextSource}
                  onRefine={handleRefine}
                  refining={refining}
                  onEditSource={setSourceToEdit}
                />
              )}

              {!loading && !result && !error && (
                <p className="text-center text-slate-500 dark:text-slate-400">
                  Enter a question above to get an answer from your snippets.
                </p>
              )}

              <div className="mt-12 border-t border-slate-200 pt-8 dark:border-slate-700">
                <button
                  type="button"
                  onClick={() => setTab("collection")}
                  className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  Manage snippets in Collection →
                </button>
              </div>

              {/* Edit snippet modal for sources */}
              {sourceToEdit && (
                <EditSnippetModal
                  snippet={sourceToSnippet(sourceToEdit)}
                  groups={groups}
                  onSaved={handleSourceSaved}
                  onCancel={() => setSourceToEdit(null)}
                />
              )}
            </>
          )}

          {tab === "collection" && (
            <CollectionView
              selectedGroups={selectedGroups}
              onGroupsChange={refreshGroups}
              groups={groups}
            />
          )}

          {tab === "users" && user?.role === "admin" && (
            <UsersView />
          )}
        </div>
      </main>
    </div>
  );
}
