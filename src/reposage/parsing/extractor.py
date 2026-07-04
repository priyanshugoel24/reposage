from dataclasses import dataclass
from tree_sitter import Language, Parser, Node
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
from pathlib import Path


PY_LANGUAGE = Language(tspython.language())
JS_LANGUAGE = Language(tsjavascript.language())
TS_LANGUAGE = Language(tstypescript.language_typescript())
TSX_LANGUAGE = Language(tstypescript.language_tsx())


#node types we care about, per language
DEFINITION_NODES = {
    "python" : {"function_definition", "class_definition"},
    "javascript" : {"function_declaration", "class_declaration", "method_definition"},
    "typescript" : {"function_declaration", "class_declaration", "method_definition"}
}

LANGUAGE_BY_EXTENSION = {
    ".py" : ("python", PY_LANGUAGE),
    ".js" : ("javascript", JS_LANGUAGE),
    ".ts" : ("typescript", TS_LANGUAGE),
    ".tsx" : ("typescript", TSX_LANGUAGE),
    ".jsx" : ("javascript", JS_LANGUAGE)
}

COMPONENT_VALUE_TYPES = {"arrow_function", "function_expression"}


@dataclass
class Definition :
    name : str
    node_type  : str
    start_line : int
    end_line : int


def _find_name(node : Node) -> str | None :
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return name_node.text.decode("utf8")
    return None

def extract_definitions(source_code : bytes, extension : str) -> list[Definition]:
    lang_key, language = LANGUAGE_BY_EXTENSION[extension]
    target_types = DEFINITION_NODES[lang_key]

    parser = Parser(language)
    tree = parser.parse(source_code)


    definitions = []

    def walk(node : Node):
        if node.type in target_types:
            name = _find_name(node) or "<anonymous>"
            definitions.append(Definition(
                name = name,
                node_type = node.type,
                start_line = node.start_point[0] + 1,
                end_line = node.end_point[0] + 1
            ))
        elif node.type == "variable_declarator" and lang_key in ("javascript", "typescript"):
            value_node = node.child_by_field_name("value")
            name_node = node.child_by_field_name("name")
            if value_node is not None and value_node.type in COMPONENT_VALUE_TYPES and name_node is not None:
                definitions.append(Definition(
                    name = name_node.text.decode("utf8"),
                    node_type = f"const_{value_node.type}",
                    start_line = node.start_point[0] + 1,
                    end_line = node.end_point[0] + 1,
                ))

        for child in node.children:
            walk(child)
    
    walk(tree.root_node)
    return definitions

def parse_file(path : Path) -> list[Definition] :
    source_code = path.read_bytes()
    return extract_definitions(source_code, path.suffix)


    