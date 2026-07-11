from reposage.indexing.summary_store import list_repos
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from reposage.ingestion.loader import load_repo, walk_source_files
from reposage.indexing.chunk import build_chunks
from reposage.indexing.summary_store import get_summary, github_url_for, save_summary
from reposage.indexing.vectorstore import get_collection, query_collection, upsert_chunks
from reposage.rag.synthesize import generate_repo_summary, synthesize_answer
from reposage.graph.call_graph import build_call_graph, save_call_graph, load_call_graph
from reposage.graph.flow_diagram import trace_subgraph, generate_flow_diagram

app = FastAPI(title="RepoSage")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://reposage-two.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


class Citation(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    source_code: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    low_confidence: bool
    github_url: str | None


class HealthResponse(BaseModel):
    status: str


class DiagramRequest(BaseModel):
    repo_name: str
    function_name: str
    max_depth: int = 2


class AmbiguousDiagramResponse(BaseModel):
    ambiguous: bool
    candidates: list[str]


class DiagramResponse(BaseModel):
    ambiguous: bool
    mermaid: str
    node_count: int
    edge_count: int
    truncated: bool
    qualified_name: str


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
        raise HTTPException(
            status_code=400,
            detail=f"Could not access repository at '{request.source}'. Check the URL and try again."
        ) from exc
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

    call_graph = build_call_graph(source_files)
    save_call_graph(request.repo_name, call_graph)

    chunk_dicts = [_chunk_to_dict(chunk) for chunk in chunks]
    summary = generate_repo_summary(chunk_dicts)
    save_summary(request.repo_name, request.source, summary)

    return IngestResponse(
        repo_name=request.repo_name,
        files_processed=len(source_files),
        chunks_created=len(chunks),
        time_seconds=time.monotonic() - start,
        summary=summary,
    )


@app.get("/summary/{repo_name}", response_model=SummaryResponse)
def get_repo_summary(repo_name: str) -> SummaryResponse:
    stored = get_summary(repo_name)

    if stored is None:
        raise HTTPException(
            status_code=404,
            detail=f"No summary found for repo '{repo_name}'. Call /ingest first.",
        )

    return SummaryResponse(repo_name=repo_name, summary=stored["summary"])


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

    stored = get_summary(request.repo_name)
    github_url = github_url_for(stored["source"]) if stored else None

    return QueryResponse(**answer, github_url=github_url)


@app.get("/repos", response_model=list[str])
def list_ingested_repos() -> list[str]:
    return list_repos()


@app.post("/diagram", response_model=DiagramResponse | AmbiguousDiagramResponse)
def diagram(request: DiagramRequest) -> DiagramResponse | AmbiguousDiagramResponse:
    graph = load_call_graph(request.repo_name)

    if graph is None:
        raise HTTPException(
            status_code=404,
            detail=f"Repo '{request.repo_name}' has not been ingested yet.",
        )

    candidates = [
        qname for qname, data in graph.nodes(data=True)
        if data.get("name") == request.function_name
    ]

    if request.function_name in graph.nodes:
        qualified_name = request.function_name
    elif not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"No function named '{request.function_name}' found in this repo.",
        )
    elif len(candidates) == 1:
        qualified_name = candidates[0]
    else:
        return AmbiguousDiagramResponse(ambiguous=True, candidates=candidates)

    subgraph = trace_subgraph(graph, qualified_name, max_depth=request.max_depth)
    result = generate_flow_diagram(subgraph, qualified_name)

    return DiagramResponse(
        ambiguous=False,
        mermaid=result["mermaid"],
        node_count=result["node_count"],
        edge_count=result["edge_count"],
        truncated=result["truncated"],
        qualified_name=qualified_name,
    )
