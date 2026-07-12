"use client";

import { FormEvent, useState } from "react";
import { ApiError, ingestRepo } from "@/lib/api";
import Modal from "@/components/Modal";

interface IngestModalProps {
  onClose: () => void;
  onIngested: (repoName: string) => void;
  initialSource?: string;
  initialRepoName?: string;
}

export default function IngestModal({
  onClose,
  onIngested,
  initialSource = "",
  initialRepoName = "",
}: IngestModalProps) {
  const [source, setSource] = useState(initialSource);
  const [repoName, setRepoName] = useState(initialRepoName);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isReingest = initialRepoName !== "";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await ingestRepo(source, repoName);
      onIngested(response.repo_name);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reach the server.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Modal onClose={onClose} title={isReingest ? "Re-ingest repository" : "Ingest a repository"}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="font-mono text-xs uppercase tracking-wide text-text-muted">
            GitHub URL
          </label>
          <input
            type="text"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="https://github.com/org/repo"
            required
            disabled={isLoading}
            className="rounded-md border border-border-strong bg-surface px-3 py-2 font-mono text-sm text-text-primary placeholder:text-text-muted disabled:opacity-60"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="font-mono text-xs uppercase tracking-wide text-text-muted">
            Repo name
          </label>
          <input
            type="text"
            value={repoName}
            onChange={(e) => setRepoName(e.target.value)}
            placeholder="org/repo"
            required
            disabled={isLoading || isReingest}
            className="rounded-md border border-border-strong bg-surface px-3 py-2 font-mono text-sm text-text-primary placeholder:text-text-muted disabled:opacity-60"
          />
        </div>

        {error && <p className="text-sm text-danger">{error}</p>}

        <div className="mt-2 flex items-center justify-end gap-4">
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="font-mono text-sm text-text-secondary hover:text-text-primary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isLoading}
            className="rounded-md bg-accent px-4 py-2 font-mono text-sm font-bold text-accent-foreground disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? "Ingesting..." : isReingest ? "Re-ingest" : "Start ingesting"}
          </button>
        </div>

        {isLoading && (
          <p className="text-xs text-text-muted">Ingesting... this can take up to 30 seconds</p>
        )}
      </form>
    </Modal>
  );
}
