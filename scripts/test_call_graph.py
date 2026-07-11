from reposage.ingestion.loader import load_repo, walk_source_files
from reposage.graph.call_graph import save_call_graph, load_call_graph, get_callers, get_callees, trace_path, build_call_graph

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


save_call_graph("medmemory-mcp", graph)
loaded = load_call_graph("medmemory-mcp")

print(f"Loaded graph: {loaded.number_of_nodes()} nodes, {loaded.number_of_edges()} edges")

target = "medmemory/db/database.py::get_active_medications"
callers = get_callers(loaded, target)
print(f"\nWho calls {target}?")
for c in callers:
    print(f"  {c}")

path = trace_path(loaded, "medmemory/server.py::check_drug_interaction", target)
print(f"\nPath from check_drug_interaction to get_active_medications: {path}")
