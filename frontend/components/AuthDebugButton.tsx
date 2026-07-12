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
    <div className="flex flex-col items-start gap-2 rounded-md border border-dashed border-warning/50 p-3 text-sm">
      <span className="font-mono text-xs text-warning">
        [TEMP] Backend auth debug — remove later
      </span>
      <button
        onClick={testBackendAuth}
        className="rounded-md border border-border-strong px-2 py-1 font-mono text-xs text-text-secondary hover:bg-surface-hover"
      >
        Test backend auth
      </button>
      {result && (
        <pre className="max-w-md overflow-x-auto whitespace-pre-wrap break-all text-left font-mono text-xs text-text-muted">
          {result}
        </pre>
      )}
    </div>
  );
}
