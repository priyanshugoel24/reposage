from tree_sitter import Language, Parser
import tree_sitter_python as tspython

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)


code = b"""
def hello(name):
    return f"hi {name}"

class Greeter :
    def greet(self):
        pass
"""


tree = parser.parse(code)
print(tree.root_node)