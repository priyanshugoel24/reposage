const API_URL = process.env.NEXT_PUBLIC_API_URL;

export async function checkHealth(): Promise<unknown> {
  const response = await fetch(`${API_URL}/health`);

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

export interface QueryResponse {
  answer: string;
  citations: string[];
  low_confidence: boolean;
}

interface ErrorResponse {
  detail: string;
}

export class ApiError extends Error {}

export async function ingestRepo(source: string, repo_name: string): Promise<IngestResponse> {
  const response = await fetch(`${API_URL}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_name, question, n_results: 5 }),
  });

  if (!response.ok) {
    const body: ErrorResponse = await response.json();
    throw new ApiError(body.detail);
  }

  return response.json();
}
