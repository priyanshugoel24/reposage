"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { RepoInfo } from "@/lib/api";
import RepoActionsMenu from "@/components/RepoActionsMenu";
import Modal from "@/components/Modal";

interface RepoCardProps {
  repo: RepoInfo;
  isSelected: boolean;
  onOpen: (repoName: string) => void;
  onReingested: (repoName: string) => void;
  onRemoved: (repoName: string) => void;
}

export default function RepoCard({ repo, isSelected, onOpen, onReingested, onRemoved }: RepoCardProps) {
  const [summaryModalOpen, setSummaryModalOpen] = useState(false);

  return (
    <div
      className={`flex flex-col gap-3 rounded-lg border bg-surface p-5 ${
        isSelected ? "border-accent" : "border-border"
      }`}
    >
      <div className="flex items-center justify-between">
        <h3 className="font-mono text-base font-bold text-text-primary">{repo.repo_name}</h3>
        {repo.language && (
          <span className="rounded-full border border-border-strong px-2 py-0.5 font-mono text-xs text-text-muted">
            {repo.language}
          </span>
        )}
      </div>

      <div className="line-clamp-3 flex-1 text-sm leading-6 text-text-secondary prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown>{repo.summary}</ReactMarkdown>
      </div>

      <button
        type="button"
        onClick={() => setSummaryModalOpen(true)}
        className="self-start font-mono text-xs text-text-muted hover:text-accent"
      >
        View full summary
      </button>

      <div className="flex items-center justify-between pt-1">
        <span className="font-mono text-xs text-text-muted">
          Ingested {new Date(repo.ingested_at).toLocaleDateString()}
        </span>
        <div className="flex items-center gap-3">
          <RepoActionsMenu repo={repo} onReingested={onReingested} onRemoved={onRemoved} />
          <button
            type="button"
            onClick={() => onOpen(repo.repo_name)}
            className="font-mono text-sm font-bold text-text-primary hover:text-accent"
          >
            Open →
          </button>
        </div>
      </div>

      {summaryModalOpen && (
        <Modal
          onClose={() => setSummaryModalOpen(false)}
          title={repo.repo_name}
          maxWidthClassName="max-w-2xl"
        >
          <div className="max-h-[70vh] overflow-y-auto prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown>{repo.summary}</ReactMarkdown>
          </div>
        </Modal>
      )}
    </div>
  );
}
