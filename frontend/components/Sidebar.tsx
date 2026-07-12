"use client";

import { useState } from "react";
import { signOut } from "next-auth/react";
import { RepoInfo } from "@/lib/api";

export type View = "repos" | "chat" | "architecture" | "tour";

interface NavItemConfig {
  view: View;
  label: string;
  icon: "dot" | "diamond" | "square";
}

const NAV_ITEMS: NavItemConfig[] = [
  { view: "repos", label: "My Repos", icon: "dot" },
  { view: "chat", label: "Chat", icon: "dot" },
  { view: "architecture", label: "Architecture", icon: "diamond" },
  { view: "tour", label: "Explore Tour", icon: "square" },
];

interface SidebarProps {
  repos: RepoInfo[];
  selectedRepo: string | null;
  onSelectRepo: (repoName: string) => void;
  activeView: View;
  onChangeView: (view: View) => void;
  userName?: string | null;
}

function NavIcon({ icon, active }: { icon: NavItemConfig["icon"]; active: boolean }) {
  const colorClass = active ? "text-accent" : "text-text-muted";
  if (icon === "diamond") {
    return <span className={`${colorClass} inline-block rotate-45 h-2 w-2 border border-current`} />;
  }
  if (icon === "square") {
    return (
      <span
        className={`${colorClass} inline-block h-2 w-2 ${active ? "bg-accent" : "border border-current"}`}
      />
    );
  }
  return (
    <span
      className={`${colorClass} inline-block h-2 w-2 rounded-full ${
        active ? "bg-accent" : "border border-current"
      }`}
    />
  );
}

export default function Sidebar({
  repos,
  selectedRepo,
  onSelectRepo,
  activeView,
  onChangeView,
  userName,
}: SidebarProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const initials = userName
    ? userName
        .split(" ")
        .map((part) => part[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "?";

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-border bg-bg-inset">
      <div className="flex items-center gap-2 px-6 py-6">
        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-accent font-mono text-sm font-bold text-accent-foreground">
          R
        </span>
        <span className="font-mono text-base font-bold text-text-primary">RepoSage</span>
      </div>

      <div className="px-4 pb-4">
        <div className="relative">
          <button
            type="button"
            onClick={() => setDropdownOpen((open) => !open)}
            disabled={repos.length === 0}
            className="flex w-full flex-col items-start gap-0.5 rounded-md border border-border-strong bg-surface px-3 py-2 text-left disabled:cursor-not-allowed"
          >
            {selectedRepo ? (
              <>
                <span className="font-mono text-sm font-bold text-text-primary">
                  {selectedRepo}
                </span>
                <span className="font-mono text-xs text-text-muted">
                  {repos.length} repo{repos.length === 1 ? "" : "s"}
                </span>
              </>
            ) : (
              <span className="font-mono text-sm text-text-muted">No repo selected</span>
            )}
          </button>

          {dropdownOpen && repos.length > 0 && (
            <div className="absolute left-0 right-0 top-full z-20 mt-1 flex max-h-64 flex-col overflow-y-auto rounded-md border border-border-strong bg-surface shadow-lg">
              {repos.map((repo) => (
                <button
                  key={repo.repo_name}
                  type="button"
                  onClick={() => {
                    onSelectRepo(repo.repo_name);
                    setDropdownOpen(false);
                  }}
                  className={`px-3 py-2 text-left font-mono text-sm hover:bg-surface-hover ${
                    repo.repo_name === selectedRepo ? "text-accent" : "text-text-primary"
                  }`}
                >
                  {repo.repo_name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-4">
        {NAV_ITEMS.map((item) => {
          const active = activeView === item.view;
          return (
            <button
              key={item.view}
              type="button"
              onClick={() => onChangeView(item.view)}
              className={`flex items-center gap-2.5 rounded-md px-3 py-2 font-mono text-sm ${
                active
                  ? "bg-surface font-bold text-text-primary"
                  : "text-text-secondary hover:bg-surface-hover"
              }`}
            >
              <NavIcon icon={item.icon} active={active} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="border-t border-border px-4 py-4">
        <button
          type="button"
          onClick={() => signOut()}
          className="flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left hover:bg-surface-hover"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-surface-hover font-mono text-xs font-bold text-text-secondary">
            {initials}
          </span>
          <span className="truncate text-sm text-text-primary">{userName ?? "Signed out"}</span>
        </button>
      </div>
    </aside>
  );
}
