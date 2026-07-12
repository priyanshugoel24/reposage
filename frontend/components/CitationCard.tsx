"use client";

import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import {
  oneDark,
  oneLight,
} from "react-syntax-highlighter/dist/esm/styles/prism";
import { Citation } from "@/lib/api";

interface CitationCardProps {
  citation: Citation;
  githubUrl?: string | null;
  index?: number;
  isExpanded: boolean;
  onToggle: () => void;
  onViewInArchitecture?: (filePath: string) => void;
}

function languageForFile(filePath: string): string {
  const ext = filePath.slice(filePath.lastIndexOf(".") + 1).toLowerCase();
  switch (ext) {
    case "py":
      return "python";
    case "ts":
    case "tsx":
      return "typescript";
    case "js":
    case "jsx":
      return "javascript";
    default:
      return "text";
  }
}

export default function CitationCard({
  citation,
  githubUrl,
  index,
  isExpanded,
  onToggle,
  onViewInArchitecture,
}: CitationCardProps) {
  const { file_path, start_line, end_line, source_code } = citation;
  const language = languageForFile(file_path);

  return (
    <div className="overflow-hidden rounded-md border border-border bg-bg-inset">
      <div
        role="button"
        tabIndex={0}
        onClick={onToggle}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onToggle();
          }
        }}
        className="flex cursor-pointer select-none items-center justify-between gap-2 border-b border-border px-3 py-2"
      >
        <div className="flex min-w-0 items-center gap-2">
          <span
            className={`inline-block shrink-0 text-text-muted transition-transform ${
              isExpanded ? "rotate-90" : ""
            }`}
          >
            ▶
          </span>
          {githubUrl ? (
            <a
              href={`${githubUrl}/blob/main/${file_path}#L${start_line}-L${end_line}`}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="truncate font-mono text-xs font-bold text-text-primary hover:text-accent"
            >
              {file_path}
            </a>
          ) : (
            <span className="truncate font-mono text-xs font-bold text-text-primary">
              {file_path}
            </span>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-3 pl-2">
          {onViewInArchitecture && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onViewInArchitecture(file_path);
              }}
              className="font-mono text-xs text-text-muted hover:text-accent"
            >
              View in architecture
            </button>
          )}
          <span className="font-mono text-xs text-text-muted">
            lines {start_line}–{end_line}
          </span>
        </div>
      </div>

      {isExpanded && (
        <div className="[&_pre]:!m-0">
          <SyntaxHighlighter
            language={language}
            style={oneLight}
            customStyle={{ margin: 0, background: "var(--color-bg-inset)", fontSize: "0.75rem" }}
            className="block dark:hidden"
          >
            {source_code}
          </SyntaxHighlighter>
          <SyntaxHighlighter
            language={language}
            style={oneDark}
            customStyle={{ margin: 0, background: "var(--color-bg-inset)", fontSize: "0.75rem" }}
            className="hidden dark:block"
          >
            {source_code}
          </SyntaxHighlighter>
        </div>
      )}

      {index !== undefined && (
        <div className="border-t border-border px-3 py-1.5 font-mono text-xs text-text-muted">
          reference [{index + 1}]
        </div>
      )}
    </div>
  );
}
