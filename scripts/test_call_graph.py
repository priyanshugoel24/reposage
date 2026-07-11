from reposage.ingestion.loader import load_repo, walk_source_files
from reposage.graph.call_graph import build_call_graph

repo_root = load_repo("https://github.com/priyanshugoel24/medmemory-mcp")
files = walk_source_files(repo_root)

graph = build_call_graph(files)

print(f"Total nodes: {graph.number_of_nodes()}")
print(f"Total edges: {graph.number_of_edges()}")

# spot check: does check_drug_interaction in server.py have exactly one outgoing edge?
target = "medmemory/server.py::check_drug_interaction"
print(f"\nOutgoing edges from {target}:")
for _, callee, data in graph.out_edges(target, data=True):
    print(f"  -> {callee}  (line {data['line']}, ambiguous={data['ambiguous']})")