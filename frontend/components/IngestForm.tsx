"use client";

import { FormEvent, useState } from "react";
import { ApiError, ingestRepo, IngestResponse } from "@/lib/api";
import ReactMarkdown from "react-markdown";

export default function IngestForm() {
  const [source, setSource] = useState("");
  const [repoName, setRepoName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isLoading) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await ingestRepo(source, repoName);
      setResult(response);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reach the server.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex w-full max-w-xl flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          type="text"
          value={source}
          onChange={(e) => setSource(e.target.value)}
          placeholder="GitHub URL or local path"
          required
          disabled={isLoading}
          className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-black disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
        />
        <input
          type="text"
          value={repoName}
          onChange={(e) => setRepoName(e.target.value)}
          placeholder="Repo name"
          required
          disabled={isLoading}
          className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-black disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-black"
        >
          {isLoading ? "Ingesting..." : "Ingest repo"}
        </button>
      </form>

      {isLoading && (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Ingesting... this can take up to 30 seconds
        </p>
      )}

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      {result && (
        <div className="flex flex-col gap-2 rounded-md border border-zinc-300 bg-zinc-50 p-4 text-sm text-black dark:border-zinc-700 dark:bg-zinc-900 dark:text-white">
          <p>Files processed: {result.files_processed}</p>
          <p>Chunks created: {result.chunks_created}</p>
          <p>Time: {result.time_seconds.toFixed(1)}s</p>
          <div className="pt-2 text-zinc-700 dark:text-zinc-300">
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown>{result.summary}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
