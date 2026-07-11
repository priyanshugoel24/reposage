"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

// TEMPORARY debug component to verify frontend/backend auth wiring. Remove once auth is fully built out.
export default function AuthDebugButton() {
  const [result, setResult] = useState<string | null>(null);

  async function testBackendAuth() {
    try {
      const response = await fetch(`${API_URL}/auth/whoami`, {
        credentials: "include",
      });
      const body = await response.text();
      setResult(`${response.status}: ${body}`);
    } catch (err) {
      setResult(`error: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  return (
    <div className="flex flex-col items-center gap-2 rounded border border-dashed border-amber-500 p-3 text-sm">
      <span className="text-amber-600 dark:text-amber-400">
        [TEMP] Backend auth debug — remove later
      </span>
      <button
        onClick={testBackendAuth}
        className="rounded border border-zinc-300 px-2 py-1 text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
      >
        Test backend auth
      </button>
      {result && (
        <pre className="max-w-md overflow-x-auto whitespace-pre-wrap break-all text-left text-xs text-zinc-600 dark:text-zinc-400">
          {result}
        </pre>
      )}
    </div>
  );
}
