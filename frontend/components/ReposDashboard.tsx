"use client";

import { useState } from "react";
import { RepoInfo } from "@/lib/api";
import RepoCard from "@/components/RepoCard";
import IngestModal from "@/components/IngestModal";

interface ReposDashboardProps {
  repos: RepoInfo[];
  selectedRepo: string | null;
  onOpenRepo: (repoName: string) => void;
  onIngested: (repoName: string) => void;
  onRepoDeleted: (repoName: string) => void;
}

export default function ReposDashboard({
  repos,
  selectedRepo,
  onOpenRepo,
  onIngested,
  onRepoDeleted,
}: ReposDashboardProps) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div className="flex flex-col gap-8 p-10">
      <div className="flex items-center justify-between border-b border-border pb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">My Repos</h1>
          <p className="mt-1 text-sm text-text-muted">Repositories you&apos;ve ingested</p>
        </div>
        <button
          type="button"
          onClick={() => setModalOpen(true)}
          className="rounded-md bg-accent px-4 py-2 font-mono text-sm font-bold text-accent-foreground hover:bg-accent-strong"
        >
          + Ingest repository
        </button>
      </div>

      {repos.length === 0 ? (
        <p className="text-sm text-text-muted">
          No repositories yet. Ingest one to get started.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {repos.map((repo) => (
            <RepoCard
              key={repo.repo_name}
              repo={repo}
              isSelected={repo.repo_name === selectedRepo}
              onOpen={onOpenRepo}
              onReingested={onIngested}
              onRemoved={onRepoDeleted}
            />
          ))}
        </div>
      )}

      {modalOpen && (
        <IngestModal onClose={() => setModalOpen(false)} onIngested={onIngested} />
      )}
    </div>
  );
}
