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
    <div className="flex flex-col gap-4">
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled || isLoading}
        className="self-start rounded-md bg-accent px-4 py-2 font-mono text-sm font-bold text-accent-foreground disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isLoading ? "Loading..." : "Show codebase map"}
      </button>

      {isLoading && <p className="text-sm text-text-muted">Loading...</p>}

      {error && <p className="text-sm text-danger">{error}</p>}

      {result && (
        <div className="flex flex-col gap-6 rounded-md border border-border bg-bg-inset p-5">
          <div className="flex flex-col gap-2">
            <h3 className="font-mono text-xs font-bold uppercase tracking-wide text-text-muted">
              Entry points
            </h3>
            <div className="max-h-64 overflow-y-auto rounded-md border border-border bg-surface p-3 font-mono text-xs text-text-secondary">
              {result.entry_points.length === 0 ? (
                <p className="text-text-muted">No entry points found.</p>
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
            <h3 className="font-mono text-xs font-bold uppercase tracking-wide text-text-muted">
              Module dependencies
            </h3>
            {sortedEdges.length === 0 ? (
              <p className="text-sm text-text-muted">No module dependencies found.</p>
            ) : (
              <div className="max-h-64 overflow-y-auto rounded-md border border-border">
                <table className="w-full text-left font-mono text-xs text-text-secondary">
                  <thead className="sticky top-0 bg-surface text-text-primary">
                    <tr>
                      <th className="px-3 py-2 font-bold">Source</th>
                      <th className="px-3 py-2 font-bold">Target</th>
                      <th className="px-3 py-2 font-bold">Calls</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedEdges.map((edge, index) => (
                      <tr
                        key={`${edge.source}-${edge.target}-${index}`}
                        className="border-t border-border"
                      >
                        <td className="px-3 py-2">{edge.source}</td>
                        <td className="px-3 py-2">{edge.target}</td>
                        <td className="px-3 py-2">{edge.call_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <h3 className="font-mono text-xs font-bold uppercase tracking-wide text-text-muted">
              Suggested reading order
            </h3>
            {result.reading_order.length === 0 ? (
              <p className="text-sm text-text-muted">No reading order available.</p>
            ) : (
              <ol className="flex list-decimal flex-col gap-1 pl-5 font-mono text-xs text-text-secondary">
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
