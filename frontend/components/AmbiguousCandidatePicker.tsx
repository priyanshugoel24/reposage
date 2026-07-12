"use client";

import { useState } from "react";

interface AmbiguousCandidatePickerProps {
  candidates: string[];
  isLoading: boolean;
  onResolve: (candidate: string) => void;
}

/** Dropdown-to-resolve UI shown when a plain function name matches more than one
 * qualified name in the call graph. Shared by DiagramForm and BlastRadiusView so
 * both function-name lookups present the same disambiguation flow. */
export default function AmbiguousCandidatePicker({
  candidates,
  isLoading,
  onResolve,
}: AmbiguousCandidatePickerProps) {
  const [selected, setSelected] = useState("");

  return (
    <div className="flex flex-col gap-3 rounded-md border border-border bg-bg-inset p-4">
      <p className="text-sm text-text-secondary">Multiple functions match that name. Pick one:</p>
      <select
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        className="rounded-md border border-border-strong bg-surface px-3 py-2 font-mono text-sm text-text-primary"
      >
        <option value="" disabled>
          Select a candidate
        </option>
        {candidates.map((candidate) => (
          <option key={candidate} value={candidate}>
            {candidate}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={() => selected && onResolve(selected)}
        disabled={isLoading || !selected}
        className="self-start rounded-md bg-accent px-4 py-2 font-mono text-sm font-bold text-accent-foreground disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isLoading ? "Generating..." : "Generate"}
      </button>
    </div>
  );
}
