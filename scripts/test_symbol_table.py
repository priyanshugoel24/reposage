from reposage.ingestion.loader import load_repo, walk_source_files
from reposage.parsing.extractor import build_symbol_table


repo_root = load_repo("https://github.com/priyanshugoel24/medmemory-mcp")
files = walk_source_files(repo_root)

table = build_symbol_table(files)

print(table.get("check_interaction"))
