# RepoSage — known issues and deferred decisions

Running log of things we've deliberately punted on, so they don't quietly get
forgotten. Not a bug tracker — just honesty about tradeoffs made under a
2-hour/day budget. Update this as new tradeoffs get made, don't let it go stale.

## From week 1

### Duplicate-file handling
`server.py` and `server_hosted.py` are near-identical files (one likely a hosted
variant of the other). Query results return both with identical distances,
which clutters top-k results with redundant hits. Undecided: dedupe near-identical
chunks at index time, flag duplication explicitly as a finding ("this logic
appears in 2 files"), or leave as-is and let the LLM synthesis step handle it
implicitly. No decision made yet — revisit once frontend result display exists,
since the right answer may depend on how results are shown to a user.

### Confidence threshold calibration
`CONFIDENCE_THRESHOLD = 0.75` in `synthesize.py` was calibrated on exactly one
repo (medmemory-mcp) and two test questions (one relevant, one not). Relevant
query distances landed ~0.48–0.52; the unrelated query landed ~0.88 — a wide
gap, so 0.75 sits comfortably in the middle for this repo. This has NOT been
validated against a second, structurally different codebase. Re-test before
trusting this threshold generally — a repo with sparser docstrings/comments
could shift the whole distance distribution.

### Error messages leak internal details
`/ingest`'s 400 response on a bad git URL currently returns the raw GitPython
exception, including the local temp file path
(`/var/folders/.../reposage_xxxxx`) and the full git command line. Not a
security-critical leak for a local dev tool, but sloppy for anything demoed
live or made public. Fix before a public demo: catch the exception and return
a clean message like `"Repository not found or inaccessible: <url>"` without
the internal path.

### Structure-aware parsing gaps
Function/class extraction (tree-sitter) currently handles:
- Python: `function_definition`, `class_definition`
- JS/TS: `function_declaration`, `class_declaration`, `method_definition`,
  plus `const X = () => {}` / `const X = function() {}` patterns

Not explicitly tested:
- Python `async def` functions (should work — same node type as sync defs in
  the grammar — but never verified against a real async-heavy file)
- Class methods written as arrow functions assigned to instance properties
  (`this.foo = () => {}` in JS/TS)
- Nested/inner functions — currently the walk recurses into everything, so
  inner functions ARE captured as separate chunks. Worth deciding if that's
  actually desired (a nested helper might not deserve its own chunk) or if
  chunks should only be built for top-level definitions.

### Repo-summary generation missed a real differentiator
Tested on medmemory-mcp: the generated summary hedged on the database layer
("likely SQLite... for hosted/production") and did not mention the AES-256/
SQLCipher encryption at all — despite that being the actual headline feature
of the repo. Root cause: `select_summary_chunks()` picks whole-file chunks
plus the largest functions by line count. Encryption setup code is likely
short (a cipher config, a `PRAGMA key` call) and got crowded out by long,
verbose functions like `ingest_health_documents` (166 lines).

Fix idea, not yet implemented: before the largest-N cutoff, force-include any
chunk whose file path or symbol name matches security/architecture-relevant
keywords (`crypto`, `cipher`, `encrypt`, `auth`, `security`, `db`, `schema`)
regardless of size. "Bigger" is not the same as "architecturally important."

## Open questions for later weeks

- How should the frontend surface low-confidence answers vs normal ones —
  different visual treatment, or just the text as-is?
- Should citations become clickable links to actual GitHub line ranges
  (`github.com/.../blob/main/file.py#L85-L251`) once we know the repo's
  default branch? Currently citations are just strings, not links.
- Gemini's citation format doesn't strictly match what the system prompt
  specifies (`file:start-end` with no spaces) — actual output has been
  `file : start-end` with spaces, and multiple citations bundled into one
  parenthetical. If citations need to be parsed programmatically (e.g. for
  the clickable-link idea above), the parser needs to tolerate this variance
  rather than assume strict compliance.


Summary generation is non-deterministic in *phrasing* across identical
ingests (expected — LLM sampling). Verified on 2 runs of medmemory-mcp that
this does NOT extend to factual contradiction between runs — both correctly
identified Next.js + FastAPI + AI document ingestion. Not yet stress-tested:
would this hold on 5+ runs, or on a repo with more architectural ambiguity?
Consider setting temperature=0 in the Gemini call if strict determinism
becomes a requirement (e.g. for reproducible demos) — currently unset,
using API default.



- Citations become structured objects: {file_path, start_line, end_line, source_code} instead of plain strings
- /ingest stores source alongside the summary (extending summary_store.py's schema again — same "just re-ingest old repos, don't migrate" approach as before is fine here)


DuplicateIDError: investigated and could NOT reproduce. Directly tested
re-ingesting an existing repo_name (medmemory-mcp) twice — both times
returned a clean 200 with no error, backend log showed nothing unusual.
The Day 12 report from Claude Code claiming this error occurred was never
substantiated with an actual traceback and appears to have been an
unverified guess. Treating this as resolved / non-issue unless it
reproduces again with an actual stack trace in hand.


Railway logs show a Hugging Face Hub anonymous-request warning on every
container start (embedding model download via sentence-transformers).
Not currently blocking, but repeated container restarts could eventually
hit HF's anonymous rate limit. Fix if it becomes a problem: generate a
free HF token and set HF_TOKEN as a Railway environment variable.


Production /ingest on Railway free tier: ~118s for medmemory-mcp (33 files,
143 chunks), vs ~13s locally. Likely CPU-constrained shared container +
added network latency from GitHub archive download (two sequential HTTP
calls vs one git clone). Not a bug — a real cost of the free tier. If this
matters for a live demo, consider: pre-ingesting the demo repo ahead of
time rather than ingesting live, or upgrading the Railway plan for more
CPU.

Backend fully deployed and verified on Railway:
https://reposage-production-b926.up.railway.app
Confirmed working: /health, /ingest (slow, ~118s on free tier), /query
(fast, full citations). CORS still needs updating with the Vercel URL
once frontend is deployed (see earlier note).


Day 14 complete — RepoSage fully deployed and verified end-to-end in
production:
  Frontend: https://reposage-two.vercel.app
  Backend:  https://reposage-production-b926.up.railway.app
Verified live: health check, query against existing repo (citations +
GitHub links working), fresh ingestion through the UI (~2min on Railway
free tier), query against freshly-ingested repo. All core v1 functionality
confirmed working in production, not just localhost.


Cross-file call resolution (Day 16) uses direct Python module-to-path
conversion for import matching. Known gaps, not yet tested:
- Relative imports (`from . import x`, `from .. import y`) — not handled,
  would need proper relative-path resolution against the importing file's
  own location.
- Star imports (`from x import *`) — a call could resolve to anything in
  the starred module, but current logic only matches explicit import
  paths, so a star-imported symbol would likely fall through to the
  ambiguous/full-candidate-list path incorrectly, even when unambiguous.
- JS/TS imports use best-effort relative-path string matching, not full
  path resolution (no .tsx/.ts extension inference, no index-file
  handling) — flagged back when extract_imports was written, still true.


Aliased Python imports (`from x import y as z`) are now correctly
resolved — the alias is traced back to the real function name for symbol
lookup, and same-file name collisions are excluded when resolution came
from an alias (since the alias is unambiguous evidence of intent).
Verified via generate_health_summary, which uses three aliased imports.

Entry-point false positives remaining after alias fix: insert_visit and
insert_vaccination still show as unreached in both database.py and
database_hosted.py. Root cause not yet investigated — could be dead code,
could be a call pattern our extraction still misses (e.g. calls inside a
try/except or comprehension not properly scoped), or could be genuinely
correct if these functions truly aren't called anywhere in this repo
snapshot. Worth checking manually if this becomes user-facing.