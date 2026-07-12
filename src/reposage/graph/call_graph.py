from networkx.generators import directed
import networkx as nx
from reposage.parsing.extractor import (parse_calls, parse_imports, build_symbol_table, resolve_calls_for_file)
import json
import os
from collections import deque
from pathlib import Path
from networkx.readwrite import json_graph

GRAPH_DIR = Path(os.getenv("REPOSAGE_DATA_DIR", "."))/"call_graphs"


def _qualified_name(file_path : str, func_name : str) -> str:
    return f"{file_path}::{func_name}"



def build_call_graph(files : list) -> nx.DiGraph:
    graph = nx.DiGraph()
    symbol_table = build_symbol_table(files)


    #add every known function as a node first, so isolated functions (never called by anything) still appear in the graph
    for func_name, file_paths in symbol_table.items():
        for fp in file_paths:
            graph.add_node(_qualified_name(fp, func_name), file=fp, name=func_name)

    for f in files:
        try:
            edges = parse_calls(f.path)
            imports = parse_imports(f.path)
        except Exception:
            continue

        resolved = resolve_calls_for_file(f.relative_path, edges, imports,symbol_table)

        for r in resolved:
            caller_qname = _qualified_name(r.caller_file, r.caller_name)
            if r.caller_name == "<module>":
                continue

            for resolved_file in r.resolved_files:
                callee_qname = _qualified_name(resolved_file, r.callee_name)
                graph.add_edge(caller_qname, callee_qname, line=r.line, ambiguous=len(r.resolved_files) > 1)

    return graph

def save_call_graph(user_id : int, repo_name : str, graph : nx.DiGraph):
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    data = json_graph.node_link_data(graph)
    path = GRAPH_DIR / f"{user_id}_{repo_name}.json"
    path.write_text(json.dumps(data))

def load_call_graph(user_id : int, repo_name : str) -> nx.DiGraph | None:
    path = GRAPH_DIR / f"{user_id}_{repo_name}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return json_graph.node_link_graph(data, directed=True)


def delete_call_graph(user_id : int, repo_name : str) -> None:
    path = GRAPH_DIR / f"{user_id}_{repo_name}.json"
    path.unlink(missing_ok=True)


def get_callers(graph : nx.DiGraph, qualified_name : str) -> list[str]:
    """Who calls this function"""

    if qualified_name not in graph:
        return []
    return list(graph.predecessors(qualified_name))

def get_callees(graph : nx.DiGraph, qualified_name : str) -> list[str]:
    """What does this function call"""
    if qualified_name not in graph:
        return []
    return list(graph.successors(qualified_name))


def get_transitive_callers(graph: nx.DiGraph, qualified_name: str, max_depth: int = 3) -> nx.DiGraph:
    """BFS backward from qualified_name following incoming edges (predecessors) up to
    max_depth hops. Returns a subgraph of exactly the nodes and edges traversed."""

    subgraph = nx.DiGraph()

    if qualified_name not in graph:
        return subgraph

    visited = {qualified_name}
    queue = deque([(qualified_name, 0)])
    subgraph.add_node(qualified_name, **graph.nodes[qualified_name])

    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue

        for predecessor in graph.predecessors(node):
            subgraph.add_node(predecessor, **graph.nodes[predecessor])
            subgraph.add_edge(predecessor, node, **graph.edges[predecessor, node])

            if predecessor not in visited:
                visited.add(predecessor)
                queue.append((predecessor, depth + 1))

    return subgraph


def trace_path(graph : nx.DiGraph, start : str, end : str) -> list[str] | None:
    """Find a call path from start to end, if one exists."""

    if start not in graph or end not in graph:
        return None
    try:
        return nx.shortest_path(graph, source=start, target=end)
    except nx.NetworkXNoPath:
        return None

