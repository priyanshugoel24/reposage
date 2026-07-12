from sqlalchemy import select, func

from reposage.db.models import SessionLocal, User, Repo, Chunk as ChunkRow
from reposage.ingestion.loader import detect_primary_language, load_repo, walk_source_files
from reposage.indexing.chunk import build_chunks
from reposage.indexing.summary_store import save_summary
from reposage.indexing.vectorstore import get_collection, query_collection, upsert_chunks
from reposage.rag.synthesize import generate_repo_summary, is_low_confidence, CONFIDENCE_THRESHOLD
from reposage.graph.call_graph import build_call_graph, save_call_graph

USER_ID = 65210891
REPO_NAME = "medmemory-mcp"
SOURCE_URL = "https://github.com/priyanshugoel24/medmemory-mcp"

QUERIES = [
    "how does drug interaction checking work",
    "how does the payment refund flow work",
    "where is health document ingestion handled",
    "how are vaccination records tracked",
]


def _chunk_to_dict(chunk) -> dict:
    return {
        "file_path": chunk.file_path,
        "symbol_name": chunk.symbol_name,
        "symbol_type": chunk.symbol_type,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "source_code": chunk.source_code,
    }


def step1_diagnostic() -> Repo | None:
    print("=" * 80)
    print("STEP 1: DIAGNOSTIC (unfiltered row counts)")
    print("=" * 80)

    with SessionLocal() as session:
        user_count = session.execute(select(func.count()).select_from(User)).scalar()
        repo_count = session.execute(select(func.count()).select_from(Repo)).scalar()
        chunk_count = session.execute(select(func.count()).select_from(ChunkRow)).scalar()

        print(f"Total User rows:  {user_count}")
        print(f"Total Repo rows:  {repo_count}")
        print(f"Total Chunk rows: {chunk_count}")

        repo_row = session.scalar(
            select(Repo).where(Repo.user_id == USER_ID, Repo.repo_name == REPO_NAME)
        )
        if repo_row is not None:
            print(
                f"Repo row for user_id={USER_ID}, repo_name={REPO_NAME!r} exists: "
                f"files_processed={repo_row.files_processed}, chunks_created={repo_row.chunks_created}"
            )
        else:
            print(f"No Repo row exists for user_id={USER_ID}, repo_name={REPO_NAME!r}.")

    print()
    return repo_row


def step2_reingest_if_missing(repo_row: Repo | None) -> None:
    print("=" * 80)
    print("STEP 2: RE-INGEST (only if medmemory-mcp doesn't exist for this user)")
    print("=" * 80)

    with SessionLocal() as session:
        chunk_count_for_repo = session.execute(
            select(func.count()).select_from(ChunkRow).where(
                ChunkRow.user_id == USER_ID, ChunkRow.repo_name == REPO_NAME
            )
        ).scalar()

    if repo_row is not None and chunk_count_for_repo > 0:
        print("Repo + chunks already exist for this user — skipping re-ingestion.")
        print()
        return

    print(f"Repo/chunks missing (repo_row={repo_row is not None}, chunk_count={chunk_count_for_repo}). Re-ingesting now...")

    with SessionLocal() as session:
        user = session.get(User, USER_ID)
        if user is None:
            user = User(id=USER_ID, username=f"user_{USER_ID}")
            session.add(user)
            session.commit()
            print(f"Created missing User row for user_id={USER_ID} (required by FK on chunks/repos).")

    repo_root = load_repo(SOURCE_URL)
    source_files = walk_source_files(repo_root)
    language = detect_primary_language(source_files)

    chunks = []
    for source_file in source_files:
        chunks.extend(
            build_chunks(source_file.path, source_file.relative_path, source_file.last_modified)
        )

    collection = get_collection(USER_ID, REPO_NAME)
    upsert_chunks(collection, chunks)

    call_graph = build_call_graph(source_files)

    chunk_dicts = [_chunk_to_dict(chunk) for chunk in chunks]
    summary = generate_repo_summary(chunk_dicts)
    save_summary(
        USER_ID,
        REPO_NAME,
        SOURCE_URL,
        summary,
        files_processed=len(source_files),
        chunks_created=len(chunks),
        language=language,
    )
    save_call_graph(USER_ID, REPO_NAME, call_graph)

    print(f"Re-ingestion complete: files_processed={len(source_files)}, chunks_created={len(chunks)}")
    print()


def step3_and_4_recalibration() -> None:
    print("=" * 80)
    print("STEP 3 + 4: RECALIBRATION TEST")
    print("=" * 80)
    print(f"CONFIDENCE_THRESHOLD = {CONFIDENCE_THRESHOLD}\n")

    collection = get_collection(USER_ID, REPO_NAME)

    for query in QUERIES:
        print("-" * 80)
        print(f"QUERY: {query}")
        print("-" * 80)

        result = query_collection(collection, query, n_results=3)
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]

        results_as_dicts = []
        for meta, distance in zip(metadatas, distances):
            print(
                f"  file_path={meta['file_path']!r} "
                f"start_line={meta['start_line']} "
                f"end_line={meta['end_line']} "
                f"symbol_name={meta['symbol_name']!r} "
                f"distance={distance!r}"
            )
            results_as_dicts.append({**meta, "distance": distance})

        low_conf = is_low_confidence(results_as_dicts)
        top1_distance = results_as_dicts[0]["distance"] if results_as_dicts else None
        print(f"  -> top-1 distance = {top1_distance!r}")
        print(f"  -> is_low_confidence() = {low_conf}")
        print()


def main() -> None:
    repo_row = step1_diagnostic()
    step2_reingest_if_missing(repo_row)
    step3_and_4_recalibration()


if __name__ == "__main__":
    main()
