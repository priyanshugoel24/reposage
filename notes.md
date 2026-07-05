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