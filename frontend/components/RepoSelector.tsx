"use client";

import { useEffect } from "react";
import { getRepos } from "@/lib/api";

interface RepoSelectorProps {
  repos: string[];
  selectedRepo: string | null;
  onReposLoaded: (repos: string[]) => void;
  onSelectRepo: (repoName: string) => void;
  refreshSignal: number;
}

export default function RepoSelector({
  repos,
  selectedRepo,
  onReposLoaded,
  onSelectRepo,
  refreshSignal,
}: RepoSelectorProps) {
  useEffect(() => {
    getRepos()
      .then(onReposLoaded)
      .catch(() => onReposLoaded([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshSignal]);

  if (repos.length === 0) {
    return null;
  }

  return (
    <select
      value={selectedRepo ?? ""}
      onChange={(e) => onSelectRepo(e.target.value)}
      className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-black dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
    >
      {repos.map((repo) => (
        <option key={repo} value={repo}>
          {repo}
        </option>
      ))}
    </select>
  );
}
