"use client";

import { FormEvent, useState } from "react";
import { ApiError, queryRepo, QueryResponse } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import CitationCard from "@/components/CitationCard";

interface QueryFormProps {
  repoName: string | null;
}

export default function QueryForm({ repoName }: QueryFormProps) {
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const disabled = !repoName;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isLoading || disabled || !repoName) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await queryRepo(repoName, question);
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
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={disabled ? "Ingest a repo first" : "Ask a question about the repo"}
          required
          disabled={disabled || isLoading}
          className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-black disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
        />
        <button
          type="submit"
          disabled={disabled || isLoading}
          className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-black"
        >
          {isLoading ? "Asking..." : "Ask"}
        </button>
      </form>

      {isLoading && (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Asking...</p>
      )}

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      {result && (
        <div
          className={`flex flex-col gap-2 rounded-md border p-4 text-sm text-black dark:text-white ${
            result.low_confidence
              ? "border-l-4 border-amber-500 border-y-zinc-300 border-r-zinc-300 bg-amber-50 dark:border-y-zinc-700 dark:border-r-zinc-700 dark:bg-amber-950/30"
              : "border-zinc-300 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900"
          }`}
        >
          <div className="text-zinc-700 dark:text-zinc-300">
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown>{result.answer}</ReactMarkdown>
            </div>
          </div>

          {result.citations.length > 0 && (
            <div className="flex flex-col gap-2 pt-2">
              {result.citations.map((citation, index) => (
                <CitationCard
                  key={`${citation.file_path}-${citation.start_line}-${index}`}
                  citation={citation}
                  githubUrl={result.github_url}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
