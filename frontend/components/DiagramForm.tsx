"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { ApiError, getDiagram, GetDiagramResponse } from "@/lib/api";

interface DiagramFormProps {
  repoName: string | null;
  disabled: boolean;
}

function useIsDarkMode(): boolean {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    setIsDark(query.matches);

    function handleChange(event: MediaQueryListEvent) {
      setIsDark(event.matches);
    }

    query.addEventListener("change", handleChange);
    return () => query.removeEventListener("change", handleChange);
  }, []);

  return isDark;
}

export default function DiagramForm({ repoName, disabled }: DiagramFormProps) {
  const [functionName, setFunctionName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<GetDiagramResponse | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDark = useIsDarkMode();

  async function runDiagram(name: string) {
    if (isLoading || disabled || !repoName || !name) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await getDiagram(repoName, name);
      setResult(response);
      setSelectedCandidate("");
    } catch (err) {
      setResult(null);
      setError(err instanceof ApiError ? err.message : "Failed to reach the server.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runDiagram(functionName);
  }

  async function handleGenerateFromCandidate() {
    if (!selectedCandidate) return;
    await runDiagram(selectedCandidate);
  }

  useEffect(() => {
    if (!result || result.ambiguous || !containerRef.current) return;

    let cancelled = false;

    mermaid.initialize({
      startOnLoad: false,
      theme: isDark ? "dark" : "default",
    });

    const renderId = `diagram-${Date.now()}`;

    mermaid.render(renderId, result.mermaid).then(({ svg }) => {
      if (!cancelled && containerRef.current) {
        containerRef.current.innerHTML = svg;
      }
    });

    return () => {
      cancelled = true;
    };
  }, [result, isDark]);

  return (
    <div className="flex w-full max-w-xl flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          type="text"
          value={functionName}
          onChange={(e) => setFunctionName(e.target.value)}
          placeholder={disabled ? "Ingest a repo first" : "Function name"}
          required
          disabled={disabled || isLoading}
          className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-black disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
        />
        <button
          type="submit"
          disabled={disabled || isLoading}
          className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-black"
        >
          {isLoading ? "Generating..." : "Show diagram"}
        </button>
      </form>

      {isLoading && (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Generating...</p>
      )}

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      {result && result.ambiguous && (
        <div className="flex flex-col gap-2 rounded-md border border-zinc-300 bg-zinc-50 p-4 text-sm dark:border-zinc-700 dark:bg-zinc-900">
          <p className="text-zinc-700 dark:text-zinc-300">
            Multiple functions match that name. Pick one:
          </p>
          <select
            value={selectedCandidate}
            onChange={(e) => setSelectedCandidate(e.target.value)}
            className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-black dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
          >
            <option value="" disabled>
              Select a candidate
            </option>
            {result.candidates.map((candidate) => (
              <option key={candidate} value={candidate}>
                {candidate}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleGenerateFromCandidate}
            disabled={isLoading || !selectedCandidate}
            className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-black"
          >
            {isLoading ? "Generating..." : "Generate"}
          </button>
        </div>
      )}

      {result && !result.ambiguous && (
        <div className="flex flex-col gap-2 rounded-md border border-zinc-300 bg-zinc-50 p-4 text-sm text-black dark:border-zinc-700 dark:bg-zinc-900 dark:text-white">
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            {result.qualified_name} &middot; {result.node_count} nodes &middot;{" "}
            {result.edge_count} edges
            {result.truncated ? " · truncated" : ""}
          </p>
          <div ref={containerRef} className="overflow-x-auto" />
        </div>
      )}
    </div>
  );
}
