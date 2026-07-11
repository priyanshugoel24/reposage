import networkx as nx
from reposage.parsing.extractor import (parse_calls, parse_imports, build_symbol_table, resolve_calls_for_file)


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