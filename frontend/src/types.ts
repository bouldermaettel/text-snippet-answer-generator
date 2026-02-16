// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type MetadataValue = any;
export type SnippetMetadata = Record<string, MetadataValue> | null;

export interface SourceItem {
  id: string;
  text: string;
  title: string | null;
  snippet_confidence: number;
  source_document_url?: string | null;
  section_label?: string | null;
  metadata?: SnippetMetadata;
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
  group: string | null;
  metadata: SnippetMetadata;
}

export interface SnippetListResponse {
  snippets: SnippetItem[];
  total: number;
}

export interface User {
  id: string;
  email: string;
  role: string;
  status?: string;
  created_at?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface RefineRequest {
  original_question: string;
  original_answer: string;
  refinement_prompt: string;
  selected_source_ids: string[];
  sources: SourceItem[];
  answer_closeness: number;
}

export interface RefineResponse {
  answer: string;
  sources: SourceItem[];
  answer_confidence: number;
}
