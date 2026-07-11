"use client";

import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";
import IngestForm from "@/components/IngestForm";
import QueryForm from "@/components/QueryForm";
import DiagramForm from "@/components/DiagramForm";
import RepoSelector from "@/components/RepoSelector";

export default function Home() {
  const [status, setStatus] = useState("checking...");
  const [repos, setRepos] = useState<string[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [refreshSignal, setRefreshSignal] = useState(0);

  useEffect(() => {
    checkHealth()
      .then((data) => setStatus(JSON.stringify(data)))
      .catch((err) => setStatus(`error: ${err.message}`));
  }, []);

  function handleIngested(repoName: string) {
    setRefreshSignal((n) => n + 1);
    setSelectedRepo(repoName);
  }

  function handleSelectRepo(repoName: string) {
    setSelectedRepo(repoName);
  }

  function handleReposLoaded(loadedRepos: string[]) {
    setRepos(loadedRepos);
    setSelectedRepo((current) =>
      current && loadedRepos.includes(current) ? current : (loadedRepos[0] ?? null)
    );
  }

  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex flex-1 w-full max-w-3xl flex-col items-center justify-center gap-4 py-32 px-16 bg-white text-center dark:bg-black">
        <h1 className="text-4xl font-semibold tracking-tight text-black dark:text-zinc-50">
          RepoSage
        </h1>
        <p className="max-w-md text-lg leading-8 text-zinc-600 dark:text-zinc-400">
          Point it at a repo. Ask it anything.
        </p>
        <p className="text-sm text-zinc-500 dark:text-zinc-500">{status}</p>
        <RepoSelector
          repos={repos}
          selectedRepo={selectedRepo}
          onReposLoaded={handleReposLoaded}
          onSelectRepo={handleSelectRepo}
          refreshSignal={refreshSignal}
        />
        <IngestForm onIngested={handleIngested} />
        <QueryForm key={selectedRepo} repoName={selectedRepo} disabled={repos.length === 0} />
        <DiagramForm key={`diagram-${selectedRepo}`} repoName={selectedRepo} disabled={repos.length === 0} />
      </main>
    </div>
  );
}
