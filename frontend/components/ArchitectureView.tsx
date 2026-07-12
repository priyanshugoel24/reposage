"use client";

import DiagramForm from "@/components/DiagramForm";
import CodebaseMapView from "@/components/CodebaseMapView";
import RepoActionsMenu from "@/components/RepoActionsMenu";
import { RepoInfo } from "@/lib/api";

interface ArchitectureViewProps {
  repoName: string | null;
  repo: RepoInfo | null;
  disabled: boolean;
  onReingested: (repoName: string) => void;
  onRemoved: (repoName: string) => void;
}

export default function ArchitectureView({
  repoName,
  repo,
  disabled,
  onReingested,
  onRemoved,
}: ArchitectureViewProps) {
  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      <header className="flex items-center gap-3 border-b border-border px-8 py-5">
        <h1 className="text-xl font-bold text-text-primary">Architecture</h1>
        {repoName && (
          <span className="rounded-full border border-border-strong px-2.5 py-0.5 font-mono text-xs text-text-secondary">
            {repoName}
          </span>
        )}
        {repo && (
          <RepoActionsMenu repo={repo} onReingested={onReingested} onRemoved={onRemoved} />
        )}
      </header>

      <div className="flex flex-col gap-10 px-8 py-6">
        <section className="flex flex-col gap-3">
          <h2 className="font-mono text-xs font-bold uppercase tracking-wide text-text-muted">
            Function call diagram
          </h2>
          <DiagramForm repoName={repoName} disabled={disabled} />
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="font-mono text-xs font-bold uppercase tracking-wide text-text-muted">
            Codebase map
          </h2>
          <CodebaseMapView repoName={repoName} disabled={disabled} />
        </section>
      </div>
    </div>
  );
}
