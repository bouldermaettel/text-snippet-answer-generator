import type { AskResponse, RefineResponse, SnippetItem, SnippetListResponse, SnippetMetadata, SourceItem, TokenResponse, User } from "./types";

const BASE = "";
/** Base URL for document links (e.g. '' for same-origin, or 'http://localhost:8000' if you need to open the backend directly). */
export const DOCUMENT_BASE = (import.meta.env.VITE_API_BASE_URL as string) ?? BASE;

const AUTH_TOKEN_KEY = "auth_token";

let onUnauthorized: (() => void) | null = null;
export function setOnUnauthorized(cb: () => void): void {
  onUnauthorized = cb;
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  } catch {
    // ignore
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  } catch {
    // ignore
  }
}

function authHeaders(): Record<string, string> {
  const t = getToken();
  if (!t) return {};
  return { Authorization: `Bearer ${t}` };
}

async function checkUnauthorized(res: Response): Promise<void> {
  if (res.status === 401) {
    clearToken();
    onUnauthorized?.();
  }
}

const BACKEND_UNREACHABLE_MSG =
  "Cannot reach the backend. Is the server running on port 8000?";

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    if (res.status === 403) {
      const body = await res.json().catch(() => ({}));
      const detail = (body as { detail?: string })?.detail;
      throw new Error(detail || "Account pending approval");
    }
    const t = await res.text();
    throw new Error(t || `Login failed: ${res.status}`);
  }
  return res.json();
}

export async function register(email: string, password: string): Promise<{ message: string }> {
  const res = await fetch(`${BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const t = await res.text();
    let msg = t;
    try {
      const body = JSON.parse(t);
      if (body.detail) msg = body.detail;
    } catch {
      // use t as-is
    }
    throw new Error(msg || `Register failed: ${res.status}`);
  }
  return res.json();
}

export async function getMe(): Promise<User> {
  const res = await fetch(`${BASE}/api/auth/me`, {
    headers: authHeaders(),
  });
  await checkUnauthorized(res);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listUsers(): Promise<User[]> {
  const res = await fetch(`${BASE}/api/users`, { headers: authHeaders() });
  await checkUnauthorized(res);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function createUser(
  email: string,
  password: string,
  role: string = "user"
): Promise<User> {
  const res = await fetch(`${BASE}/api/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ email, password, role }),
  });
  await checkUnauthorized(res);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function approveUser(userId: string): Promise<User> {
  const res = await fetch(`${BASE}/api/users/${userId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ status: "active" }),
  });
  await checkUnauthorized(res);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteUser(userId: string): Promise<void> {
  const res = await fetch(`${BASE}/api/users/${userId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  await checkUnauthorized(res);
  if (!res.ok) throw new Error(await res.text());
}

export function isNetworkError(e: unknown): boolean {
  if (e instanceof TypeError) return true;
  if (e instanceof Error && e.message === "Failed to fetch") return true;
  return false;
}

export function backendUnreachableMessage(): string {
  return BACKEND_UNREACHABLE_MSG;
}

export type AskScope = "all" | "groups" | "snippets";

export async function ask(
  question: string,
  options?: {
    groupNames?: string[];
    snippetIds?: string[];
    languages?: string[];
    answerCloseness?: number;
    useHyde?: boolean;
    useKeywordRerank?: boolean;
  }
): Promise<AskResponse> {
  const body: {
    question: string;
    group_names?: string[];
    snippet_ids?: string[];
    languages?: string[];
    answer_closeness?: number;
    use_hyde?: boolean;
    use_keyword_rerank?: boolean;
  } = { question };
  if (options?.groupNames?.length) body.group_names = options.groupNames;
  if (options?.snippetIds?.length) body.snippet_ids = options.snippetIds;
  if (options?.languages?.length) body.languages = options.languages;
  if (options?.answerCloseness !== undefined) body.answer_closeness = options.answerCloseness;
  if (options?.useHyde !== undefined) body.use_hyde = options.useHyde;
  if (options?.useKeywordRerank !== undefined) body.use_keyword_rerank = options.useKeywordRerank;
  const res = await fetch(`${BASE}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  await checkUnauthorized(res);
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `Ask failed: ${res.status}`);
  }
  return res.json();
}

export async function getSnippets(
  limit = 100,
  offset = 0,
  groups?: string[] | null,
  languages?: string[] | null,
  includeTranslations?: boolean
): Promise<SnippetListResponse> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (groups?.length) {
    groups.forEach((g) => params.append("group", g));
  }
  if (languages?.length) {
    languages.forEach((l) => params.append("language", l));
  }
  if (includeTranslations) {
    params.append("include_translations", "true");
  }
  const res = await fetch(`${BASE}/api/snippets?${params}`, { headers: authHeaders() });
  await checkUnauthorized(res);
  if (!res.ok) throw new Error(`Snippets failed: ${res.status}`);
  return res.json();
}

export async function getGroups(): Promise<{ groups: string[] }> {
  const res = await fetch(`${BASE}/api/groups`, { headers: authHeaders() });
  await checkUnauthorized(res);
  if (!res.ok) throw new Error(`Groups failed: ${res.status}`);
  return res.json();
}

export async function addSnippet(
  text: string,
  title?: string,
  group?: string | null,
  metadata?: { language?: string; heading?: string; category?: string; linked_snippets?: string[] },
  anonymize?: boolean
): Promise<{ ids: string[] }> {
  const res = await fetch(`${BASE}/api/snippets`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      text,
      title: title || null,
      group: group ?? null,
      metadata: metadata ?? null,
      anonymize: anonymize ?? false,
    }),
  });
  await checkUnauthorized(res);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateSnippet(
  id: string,
  text: string,
  title?: string,
  group?: string | null,
  metadata?: SnippetMetadata
): Promise<void> {
  const res = await fetch(`${BASE}/api/snippets/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ text, title: title ?? null, group: group ?? null, metadata: metadata ?? null }),
  });
  await checkUnauthorized(res);
  if (!res.ok) throw new Error(await res.text());
}

export async function deleteSnippet(id: string): Promise<void> {
  const res = await fetch(`${BASE}/api/snippets/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  await checkUnauthorized(res);
  if (!res.ok) throw new Error(await res.text());
}

/** Fetch document with auth and open in new tab (avoids 401 on direct link). */
export async function openDocumentInNewTab(snippetId: string): Promise<void> {
  const res = await fetch(`${BASE}/api/snippets/${snippetId}/document`, {
    headers: authHeaders(),
  });
  await checkUnauthorized(res);
  if (!res.ok) throw new Error(res.status === 404 ? "Document not found" : `Failed to load document: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener,noreferrer");
}

export async function uploadSnippets(
  files: File[],
  group?: string,
  anonymize?: boolean
): Promise<{ ids: string[]; count: number; errors?: string[] }> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  if (group != null && group !== "") form.append("group", group);
  if (anonymize) form.append("anonymize", "true");
  const res = await fetch(`${BASE}/api/snippets/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  await checkUnauthorized(res);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function refineAnswer(options: {
  originalQuestion: string;
  originalAnswer: string;
  refinementPrompt: string;
  selectedSourceIds: string[];
  sources: SourceItem[];
  answerCloseness: number;
}): Promise<RefineResponse> {
  const body = {
    original_question: options.originalQuestion,
    original_answer: options.originalAnswer,
    refinement_prompt: options.refinementPrompt,
    selected_source_ids: options.selectedSourceIds,
    sources: options.sources,
    answer_closeness: options.answerCloseness,
  };
  const res = await fetch(`${BASE}/api/refine`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  await checkUnauthorized(res);
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `Refine failed: ${res.status}`);
  }
  return res.json();
}

export async function getLinkedSnippets(snippetId: string): Promise<{ snippets: SnippetItem[] }> {
  const res = await fetch(`${BASE}/api/snippets/${snippetId}/linked`, {
    headers: authHeaders(),
  });
  await checkUnauthorized(res);
  if (!res.ok) throw new Error(`Failed to fetch linked snippets: ${res.status}`);
  return res.json();
}
