const API_URL = process.env.NEXT_PUBLIC_API_URL;

// The Auth.js CSRF cookie is httpOnly, so it can't be read from document.cookie.
// Auth.js's own /api/auth/csrf endpoint hands back the matching token value,
// which the FastAPI backend expects in the X-XSRF-Token header on state-changing requests.
async function getCsrfHeaders(): Promise<Record<string, string>> {
  const response = await fetch("/api/auth/csrf", { credentials: "include" });
  const { csrfToken } = await response.json();
  return { "X-XSRF-Token": csrfToken };
}

export async function checkHealth(): Promise<unknown> {
  const response = await fetch(`${API_URL}/health`, { credentials: "include" });

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export interface IngestResponse {
  repo_name: string;
  files_processed: number;
  chunks_created: number;
  time_seconds: number;
  summary: string;
}

export interface Citation {
  file_path: string;
  start_line: number;
  end_line: number;
  source_code: string;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  low_confidence: boolean;
  github_url: string | null;
}

interface ErrorResponse {
  detail: string;
}

export class ApiError extends Error {}

export interface RepoInfo {
  repo_name: string;
  summary: string;
  language: string | null;
  files_processed: number;
  chunks_created: number;
  ingested_at: string;
  source_url: string;
}

export async function getRepos(): Promise<RepoInfo[]> {
  const response = await fetch(`${API_URL}/repos`, { credentials: "include" });

  if (!response.ok) {
    throw new Error(`Failed to fetch repos: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export interface DeleteRepoResponse {
  repo_name: string;
  deleted: boolean;
}

export async function deleteRepo(repo_name: string): Promise<DeleteRepoResponse> {
  const response = await fetch(`${API_URL}/repos/${encodeURIComponent(repo_name)}`, {
    method: "DELETE",
    headers: await getCsrfHeaders(),
    credentials: "include",
  });

  if (!response.ok) {
    const body: ErrorResponse = await response.json();
    throw new ApiError(body.detail);
  }

  return response.json();
}

export interface SummaryResponse {
  repo_name: string;
  summary: string;
}

export async function getSummary(repo_name: string): Promise<SummaryResponse> {
  const response = await fetch(`${API_URL}/summary/${encodeURIComponent(repo_name)}`, {
    credentials: "include",
  });

  if (!response.ok) {
    const body: ErrorResponse = await response.json();
    throw new ApiError(body.detail);
  }

  return response.json();
}

export async function ingestRepo(source: string, repo_name: string): Promise<IngestResponse> {
  const response = await fetch(`${API_URL}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await getCsrfHeaders()) },
    credentials: "include",
    body: JSON.stringify({ source, repo_name }),
  });

  if (!response.ok) {
    const body: ErrorResponse = await response.json();
    throw new ApiError(body.detail);
  }

  return response.json();
}

export async function queryRepo(repo_name: string, question: string): Promise<QueryResponse> {
  const response = await fetch(`${API_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await getCsrfHeaders()) },
    credentials: "include",
    body: JSON.stringify({ repo_name, question, n_results: 5 }),
  });

  if (!response.ok) {
    const body: ErrorResponse = await response.json();
    throw new ApiError(body.detail);
  }

  return response.json();
}

export interface AmbiguousDiagramResponse {
  ambiguous: true;
  candidates: string[];
}

export interface DiagramResponse {
  ambiguous: false;
  mermaid: string;
  node_count: number;
  edge_count: number;
  truncated: boolean;
  qualified_name: string;
}

export type GetDiagramResponse = AmbiguousDiagramResponse | DiagramResponse;

export async function getDiagram(
  repo_name: string,
  function_name: string,
  max_depth?: number
): Promise<GetDiagramResponse> {
  const response = await fetch(`${API_URL}/diagram`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await getCsrfHeaders()) },
    credentials: "include",
    body: JSON.stringify({
      repo_name,
      function_name,
      ...(max_depth !== undefined ? { max_depth } : {}),
    }),
  });

  if (!response.ok) {
    const body: ErrorResponse = await response.json();
    throw new ApiError(body.detail);
  }

  return response.json();
}

export interface ModuleEdge {
  source: string;
  target: string;
  call_count: number;
}

export interface CodebaseMapResponse {
  entry_points: string[];
  module_edges: ModuleEdge[];
  reading_order: string[];
}

export async function getCodebaseMap(repo_name: string): Promise<CodebaseMapResponse> {
  const response = await fetch(`${API_URL}/codebase-map/${encodeURIComponent(repo_name)}`, {
    credentials: "include",
  });

  if (!response.ok) {
    const body: ErrorResponse = await response.json();
    throw new ApiError(body.detail);
  }

  return response.json();
}

export type ArchitectureTier = "entry_point" | "core_service" | "utility";

export interface ArchitectureNode {
  id: string;
  label: string;
  tier: ArchitectureTier;
  centrality: number;
  function_count: number;
  functions: string[];
}

export interface ArchitectureEdge {
  source: string;
  target: string;
  weight: number;
}

export interface ArchitectureGraphResponse {
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
}

export async function getArchitectureGraph(repo_name: string): Promise<ArchitectureGraphResponse> {
  const response = await fetch(`${API_URL}/architecture-graph/${encodeURIComponent(repo_name)}`, {
    credentials: "include",
  });

  if (!response.ok) {
    const body: ErrorResponse = await response.json();
    throw new ApiError(body.detail);
  }

  return response.json();
}

export interface TourStep {
  module_id: string;
  label: string;
  tier: ArchitectureTier;
  title: string;
  narration: string;
  key_functions: string[];
  function_count: number;
}

export interface TourResponse {
  steps: TourStep[];
}

export async function getTour(repo_name: string): Promise<TourResponse> {
  const response = await fetch(`${API_URL}/tour/${encodeURIComponent(repo_name)}`, {
    credentials: "include",
  });

  if (!response.ok) {
    const body: ErrorResponse = await response.json();
    throw new ApiError(body.detail);
  }

  return response.json();
}
