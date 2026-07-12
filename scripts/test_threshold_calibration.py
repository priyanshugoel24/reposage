from reposage.indexing.vectorstore import get_collection, query_collection

USER_ID = 65210891
REPO_NAME = "medmemory-mcp"

RELEVANT_QUERIES = [
    "how does drug interaction checking work",
    "how are vaccination records tracked",
    "where is health document ingestion handled",
    "how does the frontend upload a document",
]

IRRELEVANT_QUERIES = [
    "how does the payment refund flow work",
    "how is the shopping cart checkout implemented",
]


def main() -> None:
    collection = get_collection(USER_ID, REPO_NAME)

    rows = []
    for label, queries in [("RELEVANT", RELEVANT_QUERIES), ("IRRELEVANT", IRRELEVANT_QUERIES)]:
        for query in queries:
            result = query_collection(collection, query, n_results=1)
            metadatas = result["metadatas"][0]
            distances = result["distances"][0]
            top_meta = metadatas[0] if metadatas else None
            top_distance = distances[0] if distances else None
            rows.append(
                {
                    "label": label,
                    "query": query,
                    "distance": top_distance,
                    "symbol_name": top_meta["symbol_name"] if top_meta else None,
                    "file_path": top_meta["file_path"] if top_meta else None,
                }
            )

    rows.sort(key=lambda r: r["distance"] if r["distance"] is not None else float("inf"))

    header = f"{'distance':>10}  {'label':<10}  {'symbol_name':<28}  {'file_path':<40}  query"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['distance']:>10.4f}  {r['label']:<10}  {str(r['symbol_name']):<28}  "
            f"{str(r['file_path']):<40}  {r['query']}"
        )


if __name__ == "__main__":
    main()
