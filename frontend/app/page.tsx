"use client";

import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";
import IngestForm from "@/components/IngestForm";
import QueryForm from "@/components/QueryForm";

export default function Home() {
  const [status, setStatus] = useState("checking...");
  const [repoName, setRepoName] = useState<string | null>(null);

  useEffect(() => {
    checkHealth()
      .then((data) => setStatus(JSON.stringify(data)))
      .catch((err) => setStatus(`error: ${err.message}`));
  }, []);

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
        <IngestForm onIngested={setRepoName} />
        <QueryForm repoName={repoName} />
      </main>
    </div>
  );
}
