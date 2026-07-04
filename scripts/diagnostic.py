from pathlib import Path
from tree_sitter import Language, Parser
import tree_sitter_typescript as tstypescript

TSX_LANGUAGE = Language(tstypescript.language_tsx())
parser = Parser(TSX_LANGUAGE)

path = Path("/Users/priyanshugoel/Desktop/MLProjects/medmemory-mcp/ui/app/layout.tsx")
source = path.read_bytes()
tree = parser.parse(source)

def print_tree(node, depth=0):
    if depth < 4:  # keep it readable
        print("  " * depth + node.type)
    for child in node.children:
        print_tree(child, depth + 1)

print_tree(tree.root_node)
print("\n--- raw file content ---")
print(source.decode("utf8"))