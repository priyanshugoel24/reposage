from collections import deque

import networkx as nx


def detect_entry_points(graph: nx.DiGraph) -> list[str]:
    """Nodes with no incoming edges — candidate entry points."""
    return [node for node in graph.nodes if graph.in_degree(node) == 0]


def detect_module_level_entry_points(module_graph: nx.DiGraph) -> set[str]:
    """Module nodes with no incoming edges from other modules — real entry files."""
    return {node for node in module_graph.nodes if module_graph.in_degree(node) == 0}


def build_module_graph(function_graph: nx.DiGraph) -> nx.DiGraph:
    """Aggregate the function-level call graph up to file level."""
    module_graph = nx.DiGraph()

    for caller, callee in function_graph.edges:
        caller_file = function_graph.nodes[caller]["file"]
        callee_file = function_graph.nodes[callee]["file"]

        if caller_file == callee_file:
            continue

        module_graph.add_node(caller_file)
        module_graph.add_node(callee_file)

        if module_graph.has_edge(caller_file, callee_file):
            module_graph[caller_file][callee_file]["call_count"] += 1
        else:
            module_graph.add_edge(caller_file, callee_file, call_count=1)

    return module_graph


def suggest_reading_order(module_graph: nx.DiGraph, entry_points: list[str]) -> list[str]:
    """Suggest a file reading order via BFS from entry-point modules."""
    entry_files = []
    seen_entry_files = set()
    for qualified_name in entry_points:
        file_path = qualified_name.split("::", 1)[0]
        if file_path not in seen_entry_files:
            seen_entry_files.add(file_path)
            entry_files.append(file_path)

    order: list[str] = []
    visited: set[str] = set()
    queue: deque[str] = deque()

    for file_path in entry_files:
        if file_path not in visited:
            visited.add(file_path)
            queue.append(file_path)

    while queue:
        current = queue.popleft()
        order.append(current)

        if current not in module_graph:
            continue

        for neighbor in module_graph.successors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    remaining = sorted(set(module_graph.nodes) - visited)
    order.extend(remaining)

    return order
