import type { AskResponse, SnippetListResponse } from "./types";

const BASE = "";

export async function ask(question: string): Promise<AskResponse> {
  const res = await fetch(`${BASE}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `Ask failed: ${res.status}`);
  }
  return res.json();
}

export async function getSnippets(limit = 100, offset = 0): Promise<SnippetListResponse> {
  const res = await fetch(`${BASE}/api/snippets?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error(`Snippets failed: ${res.status}`);
  return res.json();
}

export async function addSnippet(text: string, title?: string): Promise<{ ids: string[] }> {
  const res = await fetch(`${BASE}/api/snippets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, title: title || null }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
