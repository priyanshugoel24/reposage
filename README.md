# RepoSage

RepoSage ingests a GitHub repository and turns it into something you can talk to. Point it at a repo URL and it clones, parses, and indexes the codebase — then lets you ask natural-language questions about it and get answers with file/line citations, browse an auto-generated architecture graph, render call-flow diagrams and a codebase map, take a guided "explore tour" of the module structure, and check the blast radius of changing a given function before you touch it.

Under the hood, ingestion walks the source tree with tree-sitter to extract functions/symbols and build a call graph, embeds code chunks for semantic search, and uses an LLM to synthesize repo summaries, tour narration, and cited answers to your questions.

## Live App

- **Frontend:** https://reposage-two.vercel.app
- **Backend API:** https://reposage-a0n6.onrender.com

## Features

- **Repo ingestion** — clone a repo, parse it with tree-sitter (Python/JS/TypeScript), and build a call graph and module graph
- **Chat with citations** — ask questions about the codebase and get answers grounded in retrieved code chunks, with `(file_path:start_line-end_line)` citations
- **Architecture graph** — module-level dependency graph with PageRank-based centrality and tiering (entry point / core service / utility)
- **Diagrams & codebase map** — Mermaid call-flow diagrams for a given function, plus a suggested reading order across modules
- **Explore tour** — an LLM-narrated, dependency-ordered walkthrough of the codebase's modules
- **Blast radius** — trace transitive callers of a function to see what could break if it changes

## Architecture

- **Frontend:** Next.js (App Router) on Vercel
- **Backend:** FastAPI on Render
- **Auth:** NextAuth.js (GitHub OAuth provider) on the frontend. The backend validates the session independently via `fastapi-nextauth-jwt`, decoding the same signed JWT session cookie rather than sharing a session store.
- **Same-origin proxy:** the frontend and backend live on different domains (`reposage-two.vercel.app` / `reposage-a0n6.onrender.com`), and browsers won't reliably attach a cross-site session cookie to a request. Instead of relying on `SameSite=None` cookies, the frontend proxies all API calls through a Next.js rewrite (`/api/backend/:path* -> BACKEND_URL/:path*`), so from the browser's perspective every request stays same-origin and the session cookie is attached automatically. See `frontend/next.config.ts` and `frontend/lib/api.ts`.
- **Parsing & graph analysis:** `tree-sitter` for symbol extraction, `networkx` for the call graph, module graph, and PageRank-based centrality (used for the architecture view and tour ordering)
- **Storage:** Postgres with `pgvector` (via SQLAlchemy) for both application data (users, repos, summaries) and code-chunk embeddings/vector search
- **LLM stack:** Google Gemini (`google-genai`) — `gemini-embedding-001` for code chunk embeddings, and `gemini-3.5-flash` for chat synthesis, repo summaries, and tour narration

## Local Development

### Prerequisites

- Python 3.13+ with [uv](https://docs.astral.sh/uv/)
- Node.js 18+
- A Postgres database with the `pgvector` extension available
- A Google Gemini API key
- A GitHub OAuth app (for NextAuth)

### Backend

```bash
uv sync
uv run uvicorn reposage.api.main:app --reload
```

Backend `.env` (repo root):

```
GEMINI_API_KEY=
AUTH_SECRET=       # must match the frontend's AUTH_SECRET
AUTH_URL=          # optional locally; used to detect secure-cookie naming.
                   # should match the frontend's deployed URL in production
DATABASE_URL=      # postgres connection string, pgvector extension enabled
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend `frontend/.env.local`:

```
BACKEND_URL=              # e.g. http://localhost:8000, used server-side by the rewrite proxy
AUTH_SECRET=              # must match the backend's AUTH_SECRET
AUTH_GITHUB_ID=
AUTH_GITHUB_SECRET=
```

The frontend runs on `http://localhost:3000` and proxies `/api/backend/*` to `BACKEND_URL`.