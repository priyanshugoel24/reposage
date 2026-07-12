"use client";

import { useEffect, useState } from "react";
import { signIn, useSession } from "next-auth/react";
import { getRepos, RepoInfo } from "@/lib/api";
import Sidebar, { View } from "@/components/Sidebar";
import ReposDashboard from "@/components/ReposDashboard";
import QueryForm from "@/components/QueryForm";
import ArchitectureView from "@/components/ArchitectureView";
import ExploreTourView from "@/components/ExploreTourView";
import AuthDebugButton from "@/components/AuthDebugButton";

function SignInScreen() {
  return (
    <div className="flex flex-1 items-center justify-center bg-bg-inset px-6">
      <div className="flex max-w-lg flex-col items-center gap-6 text-center">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-accent font-mono text-base font-bold text-accent-foreground">
            R
          </span>
          <span className="font-mono text-lg font-bold text-text-primary">RepoSage</span>
        </div>

        <h1 className="text-4xl font-bold tracking-tight text-text-primary">
          Understand any codebase in minutes.
        </h1>
        <p className="text-lg leading-8 text-text-secondary">
          Point RepoSage at a GitHub repository to get an interactive architecture map, a guided
          tour, and an AI chat that cites the exact files behind every answer.
        </p>

        <button
          onClick={() => signIn("github")}
          className="flex items-center gap-2 rounded-md bg-accent px-6 py-3 font-mono text-sm font-bold text-accent-foreground hover:bg-accent-strong"
        >
          Sign in with GitHub
        </button>
        <p className="font-mono text-xs text-text-muted">
          OAuth via GitHub &middot; read-only repo access
        </p>
      </div>
    </div>
  );
}

export default function Home() {
  const { data: session, status } = useSession();
  const [repos, setRepos] = useState<RepoInfo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [refreshSignal, setRefreshSignal] = useState(0);
  const [activeView, setActiveView] = useState<View>("repos");
  const [pendingChatQuestion, setPendingChatQuestion] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    getRepos()
      .then((loadedRepos) => {
        setRepos(loadedRepos);
        setSelectedRepo((current) =>
          current && loadedRepos.some((repo) => repo.repo_name === current)
            ? current
            : (loadedRepos[0]?.repo_name ?? null)
        );
      })
      .catch(() => setRepos([]));
  }, [session, refreshSignal]);

  function handleIngested(repoName: string) {
    setRefreshSignal((n) => n + 1);
    setSelectedRepo(repoName);
    setActiveView("repos");
  }

  function handleOpenRepo(repoName: string) {
    setSelectedRepo(repoName);
    setActiveView("chat");
  }

  function handleRepoDeleted(repoName: string) {
    setSelectedRepo((current) => (current === repoName ? null : current));
    setRefreshSignal((n) => n + 1);
  }

  if (status === "loading") {
    return <div className="flex flex-1 items-center justify-center bg-bg-inset" />;
  }

  if (!session) {
    return <SignInScreen />;
  }

  const selectedRepoInfo = repos.find((repo) => repo.repo_name === selectedRepo) ?? null;

  return (
    <div className="flex flex-1">
      <Sidebar
        repos={repos}
        selectedRepo={selectedRepo}
        onSelectRepo={setSelectedRepo}
        activeView={activeView}
        onChangeView={setActiveView}
        userName={session.user?.name ?? session.user?.email}
      />

      <main className="flex flex-1 flex-col overflow-hidden bg-background">
        {activeView === "repos" && (
          <ReposDashboard
            repos={repos}
            selectedRepo={selectedRepo}
            onOpenRepo={handleOpenRepo}
            onIngested={handleIngested}
            onRepoDeleted={handleRepoDeleted}
          />
        )}
        {activeView === "chat" && (
          <QueryForm
            key={selectedRepo}
            repoName={selectedRepo}
            repo={selectedRepoInfo}
            disabled={repos.length === 0}
            onReingested={handleIngested}
            onRemoved={handleRepoDeleted}
            initialQuestion={pendingChatQuestion}
            onInitialQuestionConsumed={() => setPendingChatQuestion(null)}
          />
        )}
        {activeView === "architecture" && (
          <ArchitectureView
            key={`architecture-${selectedRepo}`}
            repoName={selectedRepo}
            repo={selectedRepoInfo}
            disabled={repos.length === 0}
            onReingested={handleIngested}
            onRemoved={handleRepoDeleted}
            onAskInChat={(question) => {
              setPendingChatQuestion(question);
              setActiveView("chat");
            }}
          />
        )}
        {activeView === "tour" && (
          <ExploreTourView
            key={`tour-${selectedRepo}`}
            repoName={selectedRepo}
            disabled={repos.length === 0}
            onExitTour={() => setActiveView("architecture")}
            onAskInChat={(question) => {
              setPendingChatQuestion(question);
              setActiveView("chat");
            }}
          />
        )}
        {activeView === "repos" && (
          <div className="px-10 pb-6">
            <AuthDebugButton />
          </div>
        )}
      </main>
    </div>
  );
}
