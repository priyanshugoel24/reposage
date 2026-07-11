from collections import defaultdict
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

@dataclass
class ImportInfo:
    module_path : str
    imported_name: str | None = None  
    alias: str | None = None 


@dataclass
class ResolvedCall:
    caller_name : str
    caller_file : str
    callee_name : str
    resolved_files : list[str]
    line : int

def _module_to_filepath(module_path : str) -> str:
    return module_path.replace(".", "/") + ".py"

def _node_text(node : Node) -> str:
    """Safely decode a tree-sitter node's text bytes, returning '' if None."""
    return node.text.decode("utf8") if node.text is not None else ""

def _extract_callee_name(function_node : Node) -> str | None:
    if function_node.type == "identifier":
        return _node_text(function_node)
    if function_node.type == "attribute":
        attr = function_node.child_by_field_name("attribute")
        return _node_text(attr) if attr else None
    if function_node.type == "member_expression":
        prop = function_node.child_by_field_name("property")
        return _node_text(prop) if prop else None
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
                stack.append(_node_text(name_node))
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
        return _node_text(name_node)
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
                    name = _node_text(name_node),
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




def build_symbol_table(files : list) -> dict[str, list[str]]:
    """Maps a function/class name -> list of relative file paths where it's defined."""
    table : dict[str, list[str]] = defaultdict(list)
    for f in files :
        definitions = parse_file(f.path)
        for d in definitions :
            table[d.name].append(f.relative_path)
    return dict(table)


def extract_imports(source_code: bytes, extension: str) -> list[ImportInfo]:
    lang_key, language = LANGUAGE_BY_EXTENSION[extension]
    parser = Parser(language)
    tree = parser.parse(source_code)

    imports: list[ImportInfo] = []

    def walk(node: Node):
        if lang_key == "python" and node.type == "import_from_statement":
            module_node = node.child_by_field_name("module_name")
            module_path = _node_text(module_node) if module_node else ""

            for child in node.children:
                if child.type == "dotted_name" and child != module_node:
                    # plain (non-aliased) imported name
                    name = _node_text(child)
                    imports.append(ImportInfo(module_path=module_path, imported_name=name))
                elif child.type == "aliased_import":
                    name_node = child.child_by_field_name("name")
                    alias_node = child.child_by_field_name("alias")
                    if name_node is not None and alias_node is not None:
                        imports.append(ImportInfo(
                            module_path=module_path,
                            imported_name=_node_text(name_node),
                            alias=_node_text(alias_node),
                        ))
        elif node.type == "import_statement":
            module_node = node.child_by_field_name("name")
            if module_node is not None:
                imports.append(ImportInfo(module_path=_node_text(module_node)))
        elif lang_key in ("javascript", "typescript") and node.type == "import_statement":
            source_node = node.child_by_field_name("source")
            if source_node is not None:
                raw = _node_text(source_node)
                imports.append(ImportInfo(module_path=raw.strip("'\"")))

        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return imports


def parse_imports(path : Path) -> list[ImportInfo]:
    source_code = path.read_bytes()
    return extract_imports(source_code, path.suffix)


def resolve_calls_for_file(
    file_relative_path: str,
    edges: list[CallEdge],
    imports: list[ImportInfo],
    symbol_table: dict[str, list[str]],
) -> list[ResolvedCall]:
    imported_files = {_module_to_filepath(imp.module_path) for imp in imports}
    alias_to_real = {imp.alias: imp.imported_name for imp in imports if imp.alias and imp.imported_name is not None}

    resolved: list[ResolvedCall] = []
    for edge in edges:
        was_alias = edge.callee_name in alias_to_real
        lookup_name = alias_to_real.get(edge.callee_name, edge.callee_name)
        candidates = symbol_table.get(lookup_name, [])
        if not candidates:
            continue

        if was_alias:
            # an alias unambiguously points at the imported symbol —
            # exclude the same-file rule, only match against imports
            reachable = [c for c in candidates if c in imported_files]
        else:
            reachable = [
                c for c in candidates
                if c == file_relative_path or c in imported_files
            ]

        final_candidates = reachable if reachable else candidates

        resolved.append(ResolvedCall(
            caller_name=edge.caller_name,
            caller_file=file_relative_path,
            callee_name=lookup_name,
            resolved_files=final_candidates,
            line=edge.line,
        ))

    return resolved