from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import json
import re
import tempfile
import urllib.error
import urllib.request
import zipfile

SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java"}
IGNORE_DIRS = {".git", "node_modules", "__pycahce__", "venv", ".venv", "dist", "build", "logs", ".github"}

EXTENSION_LABELS = {
    ".py": "PY",
    ".ts": "TS",
    ".tsx": "TS",
    ".js": "JS",
    ".jsx": "JS",
    ".md": "MD",
    ".hcl": "HCL",
}

GITHUB_URL_RE = re.compile(r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?/?$")

@dataclass
class SourceFile :
    path : Path
    relative_path : str
    extension : str
    size_bytes : int
    last_modified : float

def _parse_github_url(source: str) -> tuple[str, str] | None:
    match = GITHUB_URL_RE.search(source)
    if not match:
        return None
    return match.group(1), match.group(2)

def _get_default_branch(owner: str, repo: str) -> str:
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        request = urllib.request.Request(
            api_url, headers={"Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("default_branch", "main")
    except Exception:
        return "main"

def load_repo(source : str) -> Path:
    """Return a local Path to the repo root, downloading if source is a GitHub URL."""

    github_ref = _parse_github_url(source) if (source.startswith("http") or source.startswith("git@")) else None

    if github_ref:
        owner, repo = github_ref
        branch = _get_default_branch(owner, repo)
        archive_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"

        tmp_dir = Path(tempfile.mkdtemp(prefix="reposage_"))
        zip_path = tmp_dir / "repo.zip"
        urllib.request.urlretrieve(archive_url, zip_path)

        with zipfile.ZipFile(zip_path) as zip_file:
            zip_file.extractall(tmp_dir)

        zip_path.unlink()
        extracted_dirs = [p for p in tmp_dir.iterdir() if p.is_dir()]
        return extracted_dirs[0]

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


def detect_primary_language(files: list[SourceFile]) -> str | None:
    """Most common file extension among ingested files, mapped to a short display label."""
    if not files:
        return None

    most_common_extension, _ = Counter(f.extension for f in files).most_common(1)[0]
    if most_common_extension in EXTENSION_LABELS:
        return EXTENSION_LABELS[most_common_extension]
    return most_common_extension.lstrip(".").upper() or None

