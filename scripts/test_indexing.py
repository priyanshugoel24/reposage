from reposage.ingestion.loader import load_repo, walk_source_files
from reposage.indexing.chunk import build_chunks
from reposage.indexing.vectorstore import get_collection, upsert_chunks

repo_root = load_repo("https://github.com/priyanshugoel24/medmemory-mcp")
files = walk_source_files(repo_root)

all_chunks = []
for f in files:
    all_chunks.extend(build_chunks(f.path, f.relative_path, f.last_modified))

collection = get_collection("medmemory-mcp")
upsert_chunks(collection, all_chunks)

print(f"Chunks built: {len(all_chunks)}")
print(f"Collection count after upsert: {collection.count()}")