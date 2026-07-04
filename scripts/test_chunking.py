from reposage.ingestion.loader import load_repo, walk_source_files
from reposage.indexing.chunk import build_chunks

repo_root = load_repo("https://github.com/priyanshugoel24/medmemory-mcp")
files = walk_source_files(repo_root)

all_chunks = []
for f in files:
    chunks = build_chunks(f.path, f.relative_path, f.last_modified)
    all_chunks.extend(chunks)

print(f"Total chunks: {len(all_chunks)}")
print(f"Files with zero definitions (whole-file fallback): "
      f"{sum(1 for c in all_chunks if c.symbol_type == 'file')}")

distinct_files = {c.file_path for c in all_chunks}
print(f"Distinct files represented: {len(distinct_files)} out of 33")

for c in all_chunks[:5]:
    print(f"{c.file_path:30} {c.symbol_name:25} {c.symbol_type:20} lines {c.start_line}-{c.end_line}")

# print one full snippet to manually verify line-slicing accuracy
layout_chunk = next(c for c in all_chunks if c.file_path.endswith("layout.tsx"))
print("\n--- layout.tsx chunk source_code ---")
print(layout_chunk.source_code)