import json
from pathlib import Path

SUMMARY_PATH = Path(".reposage_summaries.json")

def save_summary(repo_name : str, source : str, summary : str) :
    data = {}
    if SUMMARY_PATH.exists():
        data = json.loads(SUMMARY_PATH.read_text())
    data[repo_name] = {"source": source, "summary": summary}
    SUMMARY_PATH.write_text(json.dumps(data, indent = 2))

def get_summary(repo_name : str) -> dict | None:
    if not SUMMARY_PATH.exists():
        return None

    data = json.loads(SUMMARY_PATH.read_text())
    return data.get(repo_name)

def github_url_for(source: str) -> str | None:
    if not (source.startswith("http://github.com/") or source.startswith("https://github.com/")):
        return None

    url = source.rstrip("/")
    if url.endswith(".git"):
        url = url[: -len(".git")]
    return url


def list_repos() -> list[str]:
    if not SUMMARY_PATH.exists():
        return []
    data = json.loads(SUMMARY_PATH.read_text())
    return list(data.keys())
