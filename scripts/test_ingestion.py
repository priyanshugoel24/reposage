from reposage.ingestion.loader import walk_source_files, load_repo
from collections import Counter

repo_root = load_repo("https://github.com/priyanshugoel24/medmemory-mcp")
files = walk_source_files(repo_root)

print(f"Total source files found: {len(files)}")
print(Counter(f.extension for f in files))
for f in files[:5]:
    print(f.relative_path, f.size_bytes, "bytes")