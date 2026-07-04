from reposage.ingestion.loader import walk_source_files, load_repo
from reposage.parsing.extractor import parse_file
from collections import Counter

repo_root = load_repo("https://github.com/priyanshugoel24/medmemory-mcp")
files = walk_source_files(repo_root)


server_file = next(f for f in files if f.relative_path == "medmemory/server.py")
definitions = parse_file(server_file.path)

print(f"Total source files found: {len(files)}")
print(Counter(f.extension for f in files))
for f in files[:5]:
    print(f.relative_path, f.size_bytes, "bytes")


for d in definitions :
    print(f"{d.node_type:20} {d.name:30} lines {d.start_line} - {d.end_line}")

print(f"\nTotal definitions found : {len(definitions)}")

#also sanity-check a .tsx file
tsx_file = next(f for f in files if f.extension == '.tsx')
tsx_defs = parse_file(tsx_file.path)
print(f"\n{tsx_file.relative_path} : {len(tsx_defs)} definitions")
