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

export default function CitationCard({ citation, githubUrl }: CitationCardProps) {
  const { file_path, start_line, end_line, source_code } = citation;
  const label = `${file_path}:${start_line}-${end_line}`;
  const language = languageForFile(file_path);

  return (
    <div className="overflow-hidden rounded-md border border-zinc-400 bg-zinc-50 text-xs dark:border-zinc-600 dark:bg-zinc-900">
      <div className="border-b border-zinc-400 px-3 py-2 font-mono text-zinc-700 dark:border-zinc-600 dark:text-zinc-300">
        {githubUrl ? (
          <a
            href={`${githubUrl}/blob/main/${file_path}#L${start_line}-L${end_line}`}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:underline"
          >
            {label}
          </a>
        ) : (
          <span>{label}</span>
        )}
      </div>
      <div className="[&_pre]:!m-0">
        <SyntaxHighlighter
          language={language}
          style={oneLight}
          customStyle={{ margin: 0, background: "var(--surface-1)", fontSize: "0.75rem" }}
          className="block dark:hidden"
        >
          {source_code}
        </SyntaxHighlighter>
        <SyntaxHighlighter
          language={language}
          style={oneDark}
          customStyle={{ margin: 0, background: "var(--surface-1)", fontSize: "0.75rem" }}
          className="hidden dark:block"
        >
          {source_code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
