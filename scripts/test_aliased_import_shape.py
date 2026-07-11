from tree_sitter import Language, Parser
import tree_sitter_python as tspython

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

code = b"""
from medmemory.db.database import get_active_medications, get_lab_trend as db_get_lab_trend
"""

tree = parser.parse(code)

def print_tree(node, depth=0):
    field = ""
    print("  " * depth + f"{node.type} [{node.start_point[0]+1}]" + field)
    for child in node.children:
        print_tree(child, depth + 1)

print_tree(tree.root_node)