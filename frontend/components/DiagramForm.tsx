"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { ApiError, getDiagram, GetDiagramResponse } from "@/lib/api";
import AmbiguousCandidatePicker from "@/components/AmbiguousCandidatePicker";

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
    <div className="flex flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex items-center gap-3">
        <input
          type="text"
          value={functionName}
          onChange={(e) => setFunctionName(e.target.value)}
          placeholder={disabled ? "Ingest a repo first" : "Function name"}
          required
          disabled={disabled || isLoading}
          className="flex-1 rounded-md border border-border-strong bg-surface px-3 py-2 font-mono text-sm text-text-primary placeholder:text-text-muted disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={disabled || isLoading}
          className="rounded-md bg-accent px-4 py-2 font-mono text-sm font-bold text-accent-foreground disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? "Generating..." : "Show diagram"}
        </button>
      </form>

      {isLoading && <p className="text-sm text-text-muted">Generating...</p>}

      {error && <p className="text-sm text-danger">{error}</p>}

      {result && result.ambiguous && (
        <AmbiguousCandidatePicker
          candidates={result.candidates}
          isLoading={isLoading}
          onResolve={runDiagram}
        />
      )}

      {result && !result.ambiguous && (
        <div className="flex flex-col gap-3 rounded-md border border-border bg-bg-inset p-4">
          <p className="font-mono text-xs text-text-muted">
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
