from reposage.ingestion.loader import load_repo, walk_source_files
from reposage.parsing.extractor import parse_imports


repo_root = load_repo("https://github.com/priyanshugoel24/medmemory-mcp")
server_path = repo_root / "medmemory" / "server.py"

imports = parse_imports(server_path)
for imp in imports:
    print(f"{imp.module_path} | imported={imp.imported_name} | alias={imp.alias}")