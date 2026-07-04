from dataclasses import dataclass
from pathlib import Path
import tempfile
import git

SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java"}
IGNORE_DIRS = {".git", "node_modules", "__pycahce__", "venv", ".venv", "dist", "build", "logs", ".github"}

@dataclass
class SourceFile :
    path : Path
    relative_path : str
    extension : str
    size_bytes : int
    last_modified : float

def load_repo(source : str) -> Path:
    """Return a local Path to the repo root, cloning if source is a URL."""

    if source.startswith("http") or source.startswith("git@"):
        tmp_dir = Path(tempfile.mkdtemp(prefix="reposage_"))
        git.Repo.clone_from(source,tmp_dir, depth=1)
        return tmp_dir
    return Path(source).resolve()

def walk_source_files(repo_root : Path) -> list[SourceFile]:
    files = []

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.suffix not in SOURCE_EXTENSIONS:
            continue

        stat = path.stat()
        files.append(SourceFile(
            path = path,
            relative_path=str(path.relative_to(repo_root)),
            extension=path.suffix,
            size_bytes=stat.st_size,
            last_modified=stat.st_mtime,
        ))
    return files

