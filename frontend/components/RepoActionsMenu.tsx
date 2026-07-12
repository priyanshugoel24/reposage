"use client";

import { useState } from "react";
import { ApiError, deleteRepo, RepoInfo } from "@/lib/api";
import IngestModal from "@/components/IngestModal";
import ConfirmDialog from "@/components/ConfirmDialog";

interface RepoActionsMenuProps {
  repo: RepoInfo;
  onReingested: (repoName: string) => void;
  onRemoved: (repoName: string) => void;
  className?: string;
}

export default function RepoActionsMenu({
  repo,
  onReingested,
  onRemoved,
  className,
}: RepoActionsMenuProps) {
  const [ingestModalOpen, setIngestModalOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleConfirmRemove() {
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await deleteRepo(repo.repo_name);
      setConfirmOpen(false);
      onRemoved(repo.repo_name);
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Failed to reach the server.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div className={`flex items-center gap-3 ${className ?? ""}`}>
      <button
        type="button"
        onClick={() => setIngestModalOpen(true)}
        className="font-mono text-xs font-bold text-accent hover:text-accent-strong"
      >
        Re-ingest
      </button>
      <button
        type="button"
        onClick={() => setConfirmOpen(true)}
        className="font-mono text-xs text-text-muted hover:text-danger"
      >
        Remove
      </button>

      {ingestModalOpen && (
        <IngestModal
          onClose={() => setIngestModalOpen(false)}
          onIngested={onReingested}
          initialSource={repo.source_url}
          initialRepoName={repo.repo_name}
        />
      )}

      {confirmOpen && (
        <ConfirmDialog
          title="Remove repository"
          message={`Remove ${repo.repo_name}? This cannot be undone.`}
          confirmLabel={isDeleting ? "Removing…" : "Remove"}
          destructive
          isConfirming={isDeleting}
          errorMessage={deleteError}
          onConfirm={handleConfirmRemove}
          onCancel={() => setConfirmOpen(false)}
        />
      )}
    </div>
  );
}
