import os
from collections import deque

import networkx as nx
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MAX_DIAGRAM_NODES = 25

SYSTEM_INSTRUCTION = """You are a codebase assistant that turns a call graph into a Mermaid flowchart.

You will be given an exact list of nodes (qualified function names) and an exact list of
directed edges (caller -> callee) extracted from real static analysis of a codebase.

Rules:
1. Output ONLY valid Mermaid flowchart syntax, starting with "flowchart TD".
2. Represent EXACTLY the nodes and edges given to you - do not invent, merge, omit, or add
   any node or edge that is not explicitly present in the input list.
3. Your only creative task is choosing short, readable labels for each node (e.g. shorten
   "medmemory/server.py::check_drug_interaction" to "check_drug_interaction").
4. Use a stable, unique Mermaid node id for each qualified name (e.g. n0, n1, n2, ...) and
   give each node a readable label in brackets, e.g. n0["check_drug_interaction"].
5. Do not include any explanation, commentary, or markdown code fences - output raw Mermaid
   syntax only.
"""


def trace_subgraph(graph: nx.DiGraph, start_qname: str, max_depth: int = 3) -> nx.DiGraph:
    """BFS outward from start_qname following outgoing edges up to max_depth hops."""

    subgraph = nx.DiGraph()

    if start_qname not in graph:
        return subgraph

    visited = {start_qname}
    queue = deque([(start_qname, 0)])
    subgraph.add_node(start_qname, **graph.nodes[start_qname])

    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue

        for successor in graph.successors(node):
            subgraph.add_node(successor, **graph.nodes[successor])
            subgraph.add_edge(node, successor, **graph.edges[node, successor])

            if successor not in visited:
                visited.add(successor)
                queue.append((successor, depth + 1))

    return subgraph


def generate_flow_diagram(subgraph: nx.DiGraph, start_qname: str) -> dict:
    node_count = subgraph.number_of_nodes()
    edge_count = subgraph.number_of_edges()
    truncated = node_count > MAX_DIAGRAM_NODES

    nodes_text = "\n".join(f"- {n}" for n in subgraph.nodes())
    edges_text = "\n".join(f"- {u} -> {v}" for u, v in subgraph.edges())

    prompt = (
        f"Start function: {start_qname}\n\n"
        f"Nodes ({node_count}):\n{nodes_text}\n\n"
        f"Edges ({edge_count}):\n{edges_text}\n\n"
        "Generate the Mermaid flowchart TD representing exactly this structure."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"system_instruction": SYSTEM_INSTRUCTION},
    )

    return {
        "mermaid": response.text,
        "node_count": node_count,
        "edge_count": edge_count,
        "truncated": truncated,
    }
