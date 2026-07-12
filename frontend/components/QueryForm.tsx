"use client";

import { FormEvent, useState } from "react";
import { ApiError, queryRepo, QueryResponse, RepoInfo } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import CitationCard from "@/components/CitationCard";
import RepoActionsMenu from "@/components/RepoActionsMenu";

interface QueryFormProps {
  repoName: string | null;
  repo: RepoInfo | null;
  disabled: boolean;
  onReingested: (repoName: string) => void;
  onRemoved: (repoName: string) => void;
}

export default function QueryForm({ repoName, repo, disabled, onReingested, onRemoved }: QueryFormProps) {
  const [question, setQuestion] = useState("");
  const [askedQuestion, setAskedQuestion] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedIndices, setExpandedIndices] = useState<Set<number>>(new Set([0]));

  function toggleCitation(index: number) {
    setExpandedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }

  const allExpanded = Boolean(
    result && result.citations.length > 0 && result.citations.every((_, i) => expandedIndices.has(i))
  );

  function toggleAllCitations() {
    if (!result) return;
    setExpandedIndices(
      allExpanded ? new Set() : new Set(result.citations.map((_, i) => i))
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isLoading || disabled || !repoName || !question.trim()) return;

    const submittedQuestion = question;
    setIsLoading(true);
    setError(null);
    setResult(null);
    setAskedQuestion(submittedQuestion);

    try {
      const response = await queryRepo(repoName, submittedQuestion);
      setResult(response);
      setExpandedIndices(response.citations.length > 0 ? new Set([0]) : new Set());
      setQuestion("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reach the server.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-1">
      <div className="flex flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-border px-8 py-5">
          <h1 className="text-xl font-bold text-text-primary">Chat</h1>
          {repoName && (
            <span className="rounded-full border border-border-strong px-2.5 py-0.5 font-mono text-xs text-text-secondary">
              {repoName}
            </span>
          )}
          {repo && (
            <RepoActionsMenu repo={repo} onReingested={onReingested} onRemoved={onRemoved} />
          )}
        </header>

        <div className="flex-1 overflow-y-auto px-8 py-6">
          {askedQuestion && (
            <div className="mb-6 flex justify-end">
              <div className="max-w-xl rounded-lg bg-surface px-4 py-3 text-sm text-text-primary">
                {askedQuestion}
              </div>
            </div>
          )}

          {isLoading && <p className="text-sm text-text-muted">Asking...</p>}

          {error && <p className="text-sm text-danger">{error}</p>}

          {result && (
            <div
              className={`prose prose-sm dark:prose-invert max-w-none text-text-secondary ${
                result.low_confidence ? "border-l-2 border-warning pl-4" : ""
              }`}
            >
              <ReactMarkdown>{result.answer}</ReactMarkdown>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="flex items-center gap-3 border-t border-border px-8 py-5">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={disabled ? "Ingest a repo first" : `Ask about ${repoName ?? "your repo"}…`}
            disabled={disabled || isLoading}
            className="flex-1 rounded-md border border-border-strong bg-surface px-4 py-3 font-mono text-sm text-text-primary placeholder:text-text-muted disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={disabled || isLoading || !question.trim()}
            className="rounded-md bg-accent px-5 py-3 font-mono text-sm font-bold text-accent-foreground disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? "Asking..." : "Send"}
          </button>
        </form>
      </div>

      {result && result.citations.length > 0 && (
        <aside className="w-96 shrink-0 overflow-y-auto border-l border-border p-5">
          <div className="mb-3 flex items-center justify-between">
            <span className="font-mono text-xs uppercase tracking-wide text-text-muted">
              Citations
            </span>
            <button
              type="button"
              onClick={toggleAllCitations}
              className="font-mono text-xs font-bold text-accent hover:text-accent-strong"
            >
              {allExpanded ? "Collapse all" : "Expand all"}
            </button>
          </div>
          <div className="flex flex-col gap-4">
            {result.citations.map((citation, index) => (
              <CitationCard
                key={`${citation.file_path}-${citation.start_line}-${index}`}
                citation={citation}
                githubUrl={result.github_url}
                index={index}
                isExpanded={expandedIndices.has(index)}
                onToggle={() => toggleCitation(index)}
              />
            ))}
          </div>
        </aside>
      )}
    </div>
  );
}
