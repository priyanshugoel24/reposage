"use client";

import { useState } from "react";
import DiagramForm from "@/components/DiagramForm";
import CodebaseMapView from "@/components/CodebaseMapView";
import ModuleArchitectureGraph from "@/components/ModuleArchitectureGraph";
import BlastRadiusView from "@/components/BlastRadiusView";
import RepoActionsMenu from "@/components/RepoActionsMenu";
import { RepoInfo } from "@/lib/api";

interface ArchitectureViewProps {
  repoName: string | null;
  repo: RepoInfo | null;
  disabled: boolean;
  onReingested: (repoName: string) => void;
  onRemoved: (repoName: string) => void;
  onAskInChat: (question: string) => void;
  initialSelectedNodeId?: string | null;
  onInitialNodeConsumed?: () => void;
}

type Tab = "graph" | "tools" | "blast-radius";

export default function ArchitectureView({
  repoName,
  repo,
  disabled,
  onReingested,
  onRemoved,
  onAskInChat,
  initialSelectedNodeId,
  onInitialNodeConsumed,
}: ArchitectureViewProps) {
  const [activeTab, setActiveTab] = useState<Tab>("graph");

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

      <div className="flex flex-col gap-6 px-8 py-6">
        <div className="flex gap-2 self-start rounded-md border border-border bg-bg-inset p-1 font-mono text-xs">
          <button
            type="button"
            onClick={() => setActiveTab("graph")}
            className={`rounded px-3 py-1.5 font-bold transition-colors ${
              activeTab === "graph"
                ? "bg-accent text-accent-foreground"
                : "text-text-secondary hover:text-text-primary"
            }`}
          >
            Module graph
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("tools")}
            className={`rounded px-3 py-1.5 font-bold transition-colors ${
              activeTab === "tools"
                ? "bg-accent text-accent-foreground"
                : "text-text-secondary hover:text-text-primary"
            }`}
          >
            Diagram &amp; codebase map
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("blast-radius")}
            className={`rounded px-3 py-1.5 font-bold transition-colors ${
              activeTab === "blast-radius"
                ? "bg-accent text-accent-foreground"
                : "text-text-secondary hover:text-text-primary"
            }`}
          >
            Blast Radius
          </button>
        </div>

        {activeTab === "graph" && (
          <section className="flex flex-col gap-3">
            <h2 className="font-mono text-xs font-bold uppercase tracking-wide text-text-muted">
              Module architecture graph
            </h2>
            <ModuleArchitectureGraph
              repoName={repoName}
              disabled={disabled}
              onAskInChat={onAskInChat}
              initialSelectedNodeId={initialSelectedNodeId}
              onInitialNodeConsumed={onInitialNodeConsumed}
            />
          </section>
        )}

        {activeTab === "tools" && (
          <div className="flex flex-col gap-10">
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
        )}

        {activeTab === "blast-radius" && (
          <section className="flex flex-col gap-3">
            <h2 className="font-mono text-xs font-bold uppercase tracking-wide text-text-muted">
              Blast radius
            </h2>
            <p className="text-sm text-text-secondary">
              See everything that transitively depends on a function, so you know what you risk
              breaking before you change it.
            </p>
            <BlastRadiusView repoName={repoName} disabled={disabled} />
          </section>
        )}
      </div>
    </div>
  );
}
