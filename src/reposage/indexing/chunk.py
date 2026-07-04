from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from reposage.parsing.extractor import parse_file, LANGUAGE_BY_EXTENSION


@dataclass
class Chunk:
    chunk_id : str
    file_path : str
    language : str
    symbol_name : str
    symbol_type : str
    start_line : int
    end_line : int
    last_modified : float
    source_code : str

def make_chunk_id(file_path : str, symbol_name : str, start_line : int) -> str:
    raw = f"{file_path}:{symbol_name}:{start_line}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]

def build_chunks(file_path : Path, relative_path : str, last_modified : float) -> list[Chunk] :
    source_code = file_path.read_bytes()
    lines = source_code.decode("utf8", errors = "replace").splitlines()

    if file_path.suffix not in LANGUAGE_BY_EXTENSION:
        return []


    lang_key, _ = LANGUAGE_BY_EXTENSION[file_path.suffix]
    definitions = parse_file(file_path)

    if not definitions:
        #whole-file fallback
        text = "\n".join(lines)
        return [Chunk(
            chunk_id = make_chunk_id(relative_path, "<file>", 1),
            file_path = relative_path,
            language = lang_key,
            symbol_name = "<file>",
            symbol_type = "file",
            start_line = 1,
            end_line = len(lines),
            last_modified=last_modified,
            source_code=text,
        )]

    chunks = []

    for d in definitions:
        #start_line/end_line are 1-indexed; slice is 0-indexed, and exclusive
        snippet = "\n".join(lines[d.start_line - 1 : d.end_line])
        chunks.append(Chunk(
            chunk_id=make_chunk_id(relative_path, d.name, d.start_line),
            file_path=relative_path,
            language=lang_key,
            symbol_name=d.name,
            symbol_type=d.node_type,
            start_line=d.start_line,
            end_line=d.end_line,
            last_modified=last_modified,
            source_code=snippet,
        ))
    return chunks