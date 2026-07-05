import json
from pathlib import Path

SUMMARY_PATH = Path(".reposage_summaries.json")

def save_summary(repo_name : str, summary : str) :
    data = {}
    if SUMMARY_PATH.exists():
        data = json.loads(SUMMARY_PATH.read_text())
    data[repo_name] = summary
    SUMMARY_PATH.write_text(json.dumps(data, indent = 2))

def get_summary(repo_name : str) -> str | None:
    if not SUMMARY_PATH.exists():
        return None

    data = json.loads(SUMMARY_PATH.read_text())
    return data.get(repo_name)