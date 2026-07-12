from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from reposage.db.models import Chunk as ChunkRow, SessionLocal
from reposage.indexing.chunk import Chunk
from reposage.rag.synthesize import client

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONALITY = 768
# The API rejects batches larger than 100 requests (BatchEmbedContentsRequest limit).
EMBEDDING_BATCH_SIZE = 100


def _embed(texts: list[str]) -> list[list[float]]:
    # The API rejects empty content parts, which occurs for empty files (e.g. bare __init__.py).
    safe_texts = [t if t.strip() else "(empty file)" for t in texts]

    embeddings: list[list[float]] = []
    for i in range(0, len(safe_texts), EMBEDDING_BATCH_SIZE):
        batch = safe_texts[i : i + EMBEDDING_BATCH_SIZE]
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch,
            config={"output_dimensionality": EMBEDDING_DIMENSIONALITY},
        )
        embeddings.extend(e.values for e in response.embeddings)
    return embeddings


class Collection:
    def __init__(self, user_id: int, repo_name: str) -> None:
        self.user_id = user_id
        self.repo_name = repo_name

    def count(self) -> int:
        with SessionLocal() as session:
            return session.scalar(
                select(func.count())
                .select_from(ChunkRow)
                .where(ChunkRow.user_id == self.user_id, ChunkRow.repo_name == self.repo_name)
            ) or 0


def get_collection(user_id: int, repo_name: str) -> Collection:
    return Collection(user_id, repo_name)


def delete_collection(user_id: int, repo_name: str) -> None:
    with SessionLocal() as session:
        session.execute(
            delete(ChunkRow).where(ChunkRow.user_id == user_id, ChunkRow.repo_name == repo_name)
        )
        session.commit()


def upsert_chunks(collection: Collection, chunks: list[Chunk]) -> None:
    if not chunks:
        return

    embeddings = _embed([c.source_code for c in chunks])

    with SessionLocal() as session:
        for chunk, embedding in zip(chunks, embeddings):
            stmt = pg_insert(ChunkRow).values(
                user_id=collection.user_id,
                repo_name=collection.repo_name,
                file_path=chunk.file_path,
                symbol_name=chunk.symbol_name,
                symbol_type=chunk.symbol_type,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                source_code=chunk.source_code,
                embedding=embedding,
            ).on_conflict_do_update(
                index_elements=["user_id", "repo_name", "file_path", "start_line"],
                set_={
                    "symbol_name": chunk.symbol_name,
                    "symbol_type": chunk.symbol_type,
                    "end_line": chunk.end_line,
                    "source_code": chunk.source_code,
                    "embedding": embedding,
                },
            )
            session.execute(stmt)
        session.commit()


def query_collection(collection: Collection, query_text: str, n_results: int = 5) -> dict:
    query_embedding = _embed([query_text])[0]

    distance = ChunkRow.embedding.cosine_distance(query_embedding).label("distance")

    with SessionLocal() as session:
        rows = session.execute(
            select(ChunkRow, distance)
            .where(ChunkRow.user_id == collection.user_id, ChunkRow.repo_name == collection.repo_name)
            .order_by(distance)
            .limit(n_results)
        ).all()

    documents = [row.Chunk.source_code for row in rows]
    metadatas = [
        {
            "file_path": row.Chunk.file_path,
            "symbol_name": row.Chunk.symbol_name,
            "symbol_type": row.Chunk.symbol_type,
            "start_line": row.Chunk.start_line,
            "end_line": row.Chunk.end_line,
        }
        for row in rows
    ]
    distances = [row.distance for row in rows]

    return {
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances],
    }
