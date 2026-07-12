"""
In-process verification of the My-Repos backend lifecycle: double-ingest
(upsert, not duplicate-row/crash), GET /repos richer shape, and DELETE
/repos/{repo_name} tearing down the DB row + Chroma collection + call
graph file. Bypasses OAuth via FastAPI dependency_overrides, same pattern
as Phase 1 Task 2. Not pytest — a standalone script, run directly.
"""

import os
import shutil
import tempfile
from pathlib import Path

DATA_DIR = Path(tempfile.mkdtemp(prefix="reposage_test_data_"))
os.environ["REPOSAGE_DATA_DIR"] = str(DATA_DIR)

from fastapi.testclient import TestClient  # noqa: E402

import reposage.api.main as main  # noqa: E402
from reposage.db.models import Repo, SessionLocal, User  # noqa: E402

FAKE_USER = User(id=999999, username="test_user", email="test@example.com")


def override_get_current_user() -> User:
    with SessionLocal() as session:
        existing = session.get(User, FAKE_USER.id)
        if existing is None:
            session.add(User(id=FAKE_USER.id, username=FAKE_USER.username, email=FAKE_USER.email))
            session.commit()
    return FAKE_USER


main.app.dependency_overrides[main.get_current_user] = override_get_current_user

_summary_call_count = {"n": 0}


def fake_generate_repo_summary(chunk_dicts) -> str:
    _summary_call_count["n"] += 1
    return f"fake summary from run #{_summary_call_count['n']}"


main.generate_repo_summary = fake_generate_repo_summary

REPO_ROOT = Path("/tmp/reposage_test_repo")
REPO_NAME = "lifecycle-test-repo"


def main_test() -> None:
    with TestClient(main.app) as client:
        print(f"Using isolated REPOSAGE_DATA_DIR={DATA_DIR}")

        # --- Double-ingest: confirm upsert, not duplicate row / crash ---
        resp1 = client.post("/ingest", json={"source": str(REPO_ROOT), "repo_name": REPO_NAME})
        print(f"First ingest: status={resp1.status_code} body={resp1.json()}")
        assert resp1.status_code == 200, f"First ingest failed: {resp1.text}"

        resp2 = client.post("/ingest", json={"source": str(REPO_ROOT), "repo_name": REPO_NAME})
        print(f"Second ingest: status={resp2.status_code} body={resp2.json()}")
        assert resp2.status_code == 200, f"Second ingest failed: {resp2.text}"

        with SessionLocal() as session:
            rows = session.query(Repo).filter(
                Repo.user_id == FAKE_USER.id, Repo.repo_name == REPO_NAME
            ).all()
        assert len(rows) == 1, f"Expected exactly 1 row after double-ingest, found {len(rows)}"
        row = rows[0]
        print(f"DB row after double-ingest: files_processed={row.files_processed}, "
              f"chunks_created={row.chunks_created}, summary={row.summary!r}, language={row.language!r}")
        assert row.summary == "fake summary from run #2", (
            f"Expected row to reflect the SECOND ingest's summary, got {row.summary!r}"
        )
        print("PASS: double-ingest upserts a single row reflecting the second run.\n")

        # --- GET /repos richer shape ---
        repos_resp = client.get("/repos")
        assert repos_resp.status_code == 200
        repos = repos_resp.json()
        print(f"GET /repos -> {repos}")
        matching = [r for r in repos if r["repo_name"] == REPO_NAME]
        assert len(matching) == 1
        repo_info = matching[0]
        for field in ("repo_name", "summary", "language", "files_processed", "chunks_created", "ingested_at"):
            assert field in repo_info, f"Missing field '{field}' in /repos response"
        assert repo_info["language"] == "PY", f"Expected language 'PY', got {repo_info['language']!r}"
        print("PASS: GET /repos returns the richer object shape with correct language.\n")

        # --- DELETE /repos/{repo_name} ---
        from reposage.indexing.vectorstore import get_collection
        from reposage.graph.call_graph import GRAPH_DIR
        import chromadb

        collection_name = f"user_{FAKE_USER.id}_{REPO_NAME}"
        chroma_client = chromadb.PersistentClient(path=str(DATA_DIR / ".chroma"))
        existing_collections_before = [c.name for c in chroma_client.list_collections()]
        print(f"Chroma collections before delete: {existing_collections_before}")
        assert collection_name in existing_collections_before

        graph_path = GRAPH_DIR / f"{FAKE_USER.id}_{REPO_NAME}.json"
        print(f"Call graph file before delete: {graph_path} exists={graph_path.exists()}")
        assert graph_path.exists()

        del_resp = client.delete(f"/repos/{REPO_NAME}")
        print(f"DELETE /repos/{REPO_NAME}: status={del_resp.status_code} body={del_resp.json()}")
        assert del_resp.status_code == 200
        assert del_resp.json() == {"repo_name": REPO_NAME, "deleted": True}

        with SessionLocal() as session:
            rows_after = session.query(Repo).filter(
                Repo.user_id == FAKE_USER.id, Repo.repo_name == REPO_NAME
            ).all()
        print(f"DB rows after delete: {len(rows_after)}")
        assert len(rows_after) == 0, "DB row still present after DELETE"

        chroma_client_after = chromadb.PersistentClient(path=str(DATA_DIR / ".chroma"))
        existing_collections_after = [c.name for c in chroma_client_after.list_collections()]
        print(f"Chroma collections after delete: {existing_collections_after}")
        assert collection_name not in existing_collections_after, "Chroma collection still present after DELETE"

        print(f"Call graph file after delete: {graph_path} exists={graph_path.exists()}")
        assert not graph_path.exists(), "Call graph file still present after DELETE"

        print("PASS: DELETE /repos/{repo_name} removed DB row + Chroma collection + call graph file.\n")

        # --- 404 on deleting a repo that doesn't exist / isn't owned by this user ---
        del_missing_resp = client.delete(f"/repos/{REPO_NAME}")
        print(f"DELETE (already gone): status={del_missing_resp.status_code} body={del_missing_resp.json()}")
        assert del_missing_resp.status_code == 404

        del_other_user_resp = client.delete("/repos/some-other-users-repo")
        print(f"DELETE (never existed): status={del_other_user_resp.status_code}")
        assert del_other_user_resp.status_code == 404

        print("PASS: DELETE 404s cleanly for missing/not-owned repos.\n")

    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    try:
        main_test()
    finally:
        shutil.rmtree(DATA_DIR, ignore_errors=True)
