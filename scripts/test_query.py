from reposage.db.models import init_db
from reposage.indexing.vectorstore import get_collection, query_collection

init_db()
init_db()

collection = get_collection(user_id=65210891, repo_name="medmemory-mcp")

queries = [
    "where is health document ingestion handled",
    "where are drug interactions checked",
    "how are vaccination records tracked",
]

for q in queries:
    print(f"\nQuery: {q}")
    results = query_collection(collection, q, n_results=3)
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        print(f"  {meta['file_path']}:{meta['start_line']}-{meta['end_line']}  "
              f"{meta['symbol_name']}  (distance {dist:.4f})")