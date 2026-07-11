"use client";

import { signIn, signOut, useSession } from "next-auth/react";

export default function AuthWidget() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return <p className="text-sm text-zinc-500">checking session...</p>;
  }

  if (session?.user) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <span className="text-zinc-700 dark:text-zinc-300">
          Signed in as {session.user.name ?? session.user.email}
        </span>
        <button
          onClick={() => signOut()}
          className="rounded border border-zinc-300 px-2 py-1 text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
        >
          Sign out
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => signIn("github")}
      className="rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
    >
      Sign in with GitHub
    </button>
  );
}
