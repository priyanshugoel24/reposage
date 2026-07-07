from reposage.parsing.extractor import CallEdge
from reposage.ingestion.loader import load_repo, walk_source_files
from reposage.parsing.extractor import (
    parse_calls, parse_imports, build_symbol_table, resolve_calls_for_file
)

repo_root = load_repo("https://github.com/priyanshugoel24/medmemory-mcp")
files = walk_source_files(repo_root)
symbol_table = build_symbol_table(files)

server_path = repo_root / "medmemory" / "server.py"
edges = parse_calls(server_path)
imports = parse_imports(server_path)

resolved = resolve_calls_for_file("medmemory/server.py", edges, imports, symbol_table)

interaction_resolved = [r for r in resolved if r.caller_name == "check_drug_interaction"]
print(f"Resolved calls from check_drug_interaction: {len(interaction_resolved)}")
for r in interaction_resolved:
    print(f"  {r.callee_name} -> {r.resolved_files}  (line {r.line})")


fake_edge = CallEdge(caller_name="some_test_caller", callee_name="check_drug_interaction", line=999)
# Use a caller file that is NEITHER medmemory/server.py NOR medmemory/server_hosted.py
fake_resolved = resolve_calls_for_file("medmemory/cli.py", [fake_edge], imports, symbol_table)
for r in fake_resolved:
    print(f"  {r.callee_name} -> {r.resolved_files}")