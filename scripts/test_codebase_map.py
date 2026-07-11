from reposage.graph.call_graph import load_call_graph
from reposage.graph.codebase_map import (
    detect_entry_points,
    build_module_graph,
    suggest_reading_order,
)

graph = load_call_graph("medmemory-mcp")
if graph is None:
    raise RuntimeError("Failed to load call graph for 'medmemory-mcp'.")

entry_points = detect_entry_points(graph)
print(f"Entry points ({len(entry_points)}):")
for ep in entry_points:
    print(f"  {ep}")

module_graph = build_module_graph(graph)
print(f"\nModule graph: {module_graph.number_of_nodes()} nodes, {module_graph.number_of_edges()} edges")
print("Edges:")
for src, dst, data in module_graph.edges(data=True):
    print(f"  {src} -> {dst}  (call_count={data['call_count']})")

reading_order = suggest_reading_order(module_graph, entry_points)
print(f"\nSuggested reading order ({len(reading_order)} files):")
for f in reading_order:
    print(f"  {f}")
