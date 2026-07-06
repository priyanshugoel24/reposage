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

CALL_NODE_TYPES = {
    "python" : {"call"},
    "javascript" : {"call_expression"},
    "typescript" : {"call_expression"}
}

COMPONENT_VALUE_TYPES = {"arrow_function", "function_expression"}


@dataclass
class Definition :
    name : str
    node_type  : str
    start_line : int
    end_line : int

@dataclass
class CallEdge:
    caller_name : str
    callee_name : str
    line : int

def _extract_callee_name(function_node : Node) -> str | None:
    if function_node.type == "identifier":
        return function_node.text.decode("utf8")
    if function_node.type == "attribute":
        attr = function_node.child_by_field_name("attribute")
        return attr.text.decode("utf8") if attr else None
    if function_node.type == "member_expression":
        prop = function_node.child_by_field_name("property")
        return prop.text.decode("utf8") if prop else None
    return None


def extract_calls(source_code : bytes, extension : str) -> list[CallEdge]:
    lang_key, language = LANGUAGE_BY_EXTENSION[extension]
    target_def_types = DEFINITION_NODES[lang_key]
    target_call_types = CALL_NODE_TYPES[lang_key]

    parser = Parser(language)
    tree = parser.parse(source_code)


    edges : list[CallEdge] = []
    stack = ["<module>"]


    def walk(node : Node):
        entered_scope = False

        if node.type in target_def_types:
            stack.append(_find_name(node) or "<anonymous>")
            entered_scope = True
        elif node.type == "variable_declarator" and lang_key in ("javascript", "typescript"):
            value_node = node.child_by_field_name("value")
            name_node = node.child_by_field_name("name")

            if value_node is not None and value_node.type in COMPONENT_VALUE_TYPES and name_node is not None:
                stack.append(name_node.text.decode("utf8"))
                entered_scope = True

        
        if node.type in target_call_types:
            function_node = node.child_by_field_name("function")
            if function_node is not None:
                callee_name = _extract_callee_name(function_node)
                if callee_name :
                    edges.append(CallEdge(
                        caller_name = stack[-1],
                        callee_name = callee_name,
                        line = node.start_point[0] + 1
                    ))


        for child in node.children:
            walk(child)

        if entered_scope:
            stack.pop()

    walk(tree.root_node)
    return edges

def parse_calls(path : Path) -> list[CallEdge]:
    source_code = path.read_bytes()
    return extract_calls(source_code, path.suffix)


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


    