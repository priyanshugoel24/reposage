from reposage.graph.call_graph import load_call_graph
from reposage.graph.flow_diagram import trace_subgraph, generate_flow_diagram
from reposage.ingestion.loader import load_repo, walk_source_files
from reposage.graph.call_graph import build_call_graph, save_call_graph

repo_root = load_repo("https://github.com/priyanshugoel24/medmemory-mcp")
files = walk_source_files(repo_root)
graph = build_call_graph(files)
save_call_graph("medmemory-mcp", graph)

# graph = load_call_graph("medmemory-mcp")
# if graph is None:
#     raise RuntimeError("Failed to load call graph for 'medmemory-mcp'.")

start = "medmemory/server.py::check_drug_interaction"
subgraph = trace_subgraph(graph, start, max_depth=2)

print(f"Subgraph nodes: {subgraph.number_of_nodes()}")
print(f"Subgraph edges: {subgraph.number_of_edges()}")
print("\nNodes:")
for n in subgraph.nodes():
    print(f"  {n}")

result = generate_flow_diagram(subgraph, start)

print(f"\nnode_count: {result['node_count']}")
print(f"edge_count: {result['edge_count']}")
print(f"truncated: {result['truncated']}")
print("\nMermaid diagram:\n")
print(result["mermaid"])

start2 = "medmemory/server.py::generate_health_summary"
subgraph2 = trace_subgraph(graph, start2, max_depth=2)

print(f"\n\n=== {start2} ===")
print(f"Subgraph nodes: {subgraph2.number_of_nodes()}")
print(f"Subgraph edges: {subgraph2.number_of_edges()}")
print("\nNodes:")
for n in subgraph2.nodes():
    print(f"  {n}")

result2 = generate_flow_diagram(subgraph2, start2)

print(f"\nnode_count: {result2['node_count']}")
print(f"edge_count: {result2['edge_count']}")
print(f"truncated: {result2['truncated']}")
print("\nMermaid diagram:\n")
print(result2["mermaid"])
