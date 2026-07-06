from reposage.parsing.extractor import parse_calls
from reposage.ingestion.loader import load_repo

repo_root = load_repo("https://github.com/priyanshugoel24/medmemory-mcp")
server_path = repo_root / "medmemory" / "server.py"

edges = parse_calls(server_path)

# filter to just this one function's calls, since the file has ~9 functions
interaction_edges = [e for e in edges if e.caller_name == "check_drug_interaction"]

print(f"Total call edges in file: {len(edges)}")
print(f"Calls made from check_drug_interaction: {len(interaction_edges)}")
for e in interaction_edges:
    print(f"  {e.caller_name} -> {e.callee_name}  (line {e.line})")