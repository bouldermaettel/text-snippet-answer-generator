export interface SourceItem {
  id: string;
  text: string;
  title: string | null;
  snippet_confidence: number;
}

export interface AskResponse {
  answer: string;
  sources: SourceItem[];
  answer_confidence: number;
}

export interface SnippetItem {
  id: string;
  text: string;
  title: string | null;
  metadata: Record<string, string> | null;
}

export interface SnippetListResponse {
  snippets: SnippetItem[];
  total: number;
}
