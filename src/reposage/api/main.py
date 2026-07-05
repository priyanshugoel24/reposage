import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from reposage.ingestion.loader import load_repo, walk_source_files
from reposage.indexing.chunk import build_chunks
from reposage.indexing.summary_store import get_summary, save_summary
from reposage.indexing.vectorstore import get_collection, query_collection, upsert_chunks
from reposage.rag.synthesize import generate_repo_summary, synthesize_answer

app = FastAPI(title="RepoSage")


class IngestRequest(BaseModel):
    source: str
    repo_name: str


class IngestResponse(BaseModel):
    repo_name: str
    files_processed: int
    chunks_created: int
    time_seconds: float
    summary: str


class SummaryResponse(BaseModel):
    repo_name: str
    summary: str


class QueryRequest(BaseModel):
    repo_name: str
    question: str
    n_results: int = 5


class QueryResponse(BaseModel):
    answer: str
    citations: list[str]
    low_confidence: bool


class HealthResponse(BaseModel):
    status: str


def _chunk_to_dict(chunk) -> dict:
    return {
        "file_path": chunk.file_path,
        "symbol_name": chunk.symbol_name,
        "symbol_type": chunk.symbol_type,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "source_code": chunk.source_code,
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest) -> IngestResponse:
    start = time.monotonic()

    try:
        repo_root = load_repo(request.source)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to load repo: {exc}") from exc

    if not repo_root.exists():
        raise HTTPException(status_code=400, detail=f"Source path does not exist: {request.source}")

    source_files = walk_source_files(repo_root)

    chunks = []
    for source_file in source_files:
        chunks.extend(
            build_chunks(source_file.path, source_file.relative_path, source_file.last_modified)
        )

    collection = get_collection(request.repo_name)
    upsert_chunks(collection, chunks)

    chunk_dicts = [_chunk_to_dict(chunk) for chunk in chunks]
    summary = generate_repo_summary(chunk_dicts)
    save_summary(request.repo_name, summary)

    return IngestResponse(
        repo_name=request.repo_name,
        files_processed=len(source_files),
        chunks_created=len(chunks),
        time_seconds=time.monotonic() - start,
        summary=summary,
    )


@app.get("/summary/{repo_name}", response_model=SummaryResponse)
def get_repo_summary(repo_name: str) -> SummaryResponse:
    summary = get_summary(repo_name)

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail=f"No summary found for repo '{repo_name}'. Call /ingest first.",
        )

    return SummaryResponse(repo_name=repo_name, summary=summary)


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    collection = get_collection(request.repo_name)

    if collection.count() == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Repo '{request.repo_name}' has not been ingested yet. Call /ingest first.",
        )

    results = query_collection(collection, request.question, n_results=request.n_results)

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    retrieved = [
        {
            "file_path": meta["file_path"],
            "symbol_name": meta["symbol_name"],
            "symbol_type": meta["symbol_type"],
            "start_line": meta["start_line"],
            "end_line": meta["end_line"],
            "source_code": doc,
            "distance": distance,
        }
        for doc, meta, distance in zip(documents, metadatas, distances)
    ]

    answer = synthesize_answer(request.question, retrieved)
    return QueryResponse(**answer)
