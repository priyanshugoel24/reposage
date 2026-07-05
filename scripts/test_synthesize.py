from reposage.indexing.vectorstore import get_collection, query_collection
from reposage.rag.synthesize import synthesize_answer

collection = get_collection("medmemory-mcp")

# a question the repo SHOULD answer well
results = query_collection(collection, "how does drug interaction checking work", n_results=5)
formatted = [
    {"file_path": m["file_path"], "symbol_name": m["symbol_name"],
     "start_line": m["start_line"], "end_line": m["end_line"],
     "source_code": doc, "distance": dist}
    for doc, m, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
]

output = synthesize_answer("how does drug interaction checking work", formatted)
print("ANSWER:\n", output["answer"])
print("\nCITATIONS PROVIDED:", output["citations"])
print("LOW CONFIDENCE:", output["low_confidence"])

# a question the repo should NOT be able to answer
results2 = query_collection(collection, "how does the payment refund flow work", n_results=5)
formatted2 = [
    {"file_path": m["file_path"], "symbol_name": m["symbol_name"],
     "start_line": m["start_line"], "end_line": m["end_line"],
     "source_code": doc, "distance": dist}
    for doc, m, dist in zip(results2["documents"][0], results2["metadatas"][0], results2["distances"][0])
]
print("Top distance for unrelated question:", formatted2[0]["distance"] if formatted2 else "no results")
output2 = synthesize_answer("how does the payment refund flow work", formatted2)
print("\n---\nUNRELATED QUESTION ANSWER:\n", output2["answer"])
print("LOW CONFIDENCE:", output2["low_confidence"])