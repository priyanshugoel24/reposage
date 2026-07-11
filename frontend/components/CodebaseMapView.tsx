"use client";

import { useState } from "react";
import { ApiError, CodebaseMapResponse, getCodebaseMap } from "@/lib/api";

interface CodebaseMapViewProps {
  repoName: string | null;
  disabled: boolean;
}

export default function CodebaseMapView({ repoName, disabled }: CodebaseMapViewProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<CodebaseMapResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    if (isLoading || disabled || !repoName) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await getCodebaseMap(repoName);
      setResult(response);
    } catch (err) {
      setResult(null);
      setError(err instanceof ApiError ? err.message : "Failed to reach the server.");
    } finally {
      setIsLoading(false);
    }
  }

  const sortedEdges = result
    ? [...result.module_edges].sort((a, b) => b.call_count - a.call_count)
    : [];

  return (
    <div className="flex w-full max-w-xl flex-col gap-4">
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled || isLoading}
        className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-black"
      >
        {isLoading ? "Loading..." : "Show codebase map"}
      </button>

      {isLoading && (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading...</p>
      )}

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      {result && (
        <div className="flex flex-col gap-6 rounded-md border border-zinc-300 bg-zinc-50 p-4 text-sm text-black dark:border-zinc-700 dark:bg-zinc-900 dark:text-white">
          <div className="flex flex-col gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Entry points
            </h3>
            <div
              className="max-h-64 overflow-y-auto rounded-md border border-zinc-400 p-2 font-mono text-xs dark:border-zinc-600"
              style={{ background: "var(--surface-1)" }}
            >
              {result.entry_points.length === 0 ? (
                <p className="text-zinc-500 dark:text-zinc-400">No entry points found.</p>
              ) : (
                <ul className="flex flex-col gap-1">
                  {result.entry_points.map((entryPoint) => (
                    <li key={entryPoint}>{entryPoint}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Module dependencies
            </h3>
            {sortedEdges.length === 0 ? (
              <p className="text-zinc-500 dark:text-zinc-400">No module dependencies found.</p>
            ) : (
              <div className="max-h-64 overflow-y-auto rounded-md border border-zinc-400 dark:border-zinc-600">
                <table className="w-full text-left font-mono text-xs">
                  <thead className="sticky top-0" style={{ background: "var(--surface-1)" }}>
                    <tr>
                      <th className="px-2 py-1 font-semibold">Source</th>
                      <th className="px-2 py-1 font-semibold">Target</th>
                      <th className="px-2 py-1 font-semibold">Calls</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedEdges.map((edge, index) => (
                      <tr
                        key={`${edge.source}-${edge.target}-${index}`}
                        className="border-t border-zinc-300 dark:border-zinc-700"
                      >
                        <td className="px-2 py-1">{edge.source}</td>
                        <td className="px-2 py-1">{edge.target}</td>
                        <td className="px-2 py-1">{edge.call_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Suggested reading order
            </h3>
            {result.reading_order.length === 0 ? (
              <p className="text-zinc-500 dark:text-zinc-400">No reading order available.</p>
            ) : (
              <ol className="flex list-decimal flex-col gap-1 pl-5 font-mono text-xs">
                {result.reading_order.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ol>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
