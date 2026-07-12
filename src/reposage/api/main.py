from datetime import datetime
from functools import lru_cache
from pathlib import Path
import math
import time

import networkx as nx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_nextauth_jwt import NextAuthJWT
from fastapi_nextauth_jwt.exceptions import NextAuthJWTException
from pydantic import BaseModel

from reposage.db.models import SessionLocal, User, init_db
from reposage.ingestion.loader import detect_primary_language, load_repo, walk_source_files
from reposage.indexing.chunk import build_chunks
from reposage.indexing.summary_store import delete_repo, get_summary, github_url_for, list_repos, save_summary
from reposage.indexing.vectorstore import delete_collection, get_collection, query_collection, upsert_chunks
from reposage.rag.synthesize import generate_repo_summary, synthesize_answer
from reposage.graph.call_graph import build_call_graph, save_call_graph, load_call_graph, delete_call_graph
from reposage.graph.flow_diagram import trace_subgraph, generate_flow_diagram
from reposage.graph.codebase_map import (
    detect_entry_points,
    detect_module_level_entry_points,
    build_module_graph,
    suggest_reading_order,
)

app = FastAPI(title="RepoSage")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://reposage-two.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@lru_cache
def get_jwt_auth() -> NextAuthJWT:
    return NextAuthJWT()


@app.exception_handler(NextAuthJWTException)
def nextauth_jwt_exception_handler(request: Request, exc: NextAuthJWTException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


def get_current_user(request: Request, jwt_auth: NextAuthJWT = Depends(get_jwt_auth)) -> User:
    claims = jwt_auth(request)
    sub = claims.get("sub")
    if sub is None:
        raise HTTPException(status_code=401, detail="Invalid session")

    user_id = int(sub)

    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user is None:
            user = User(
                id=user_id,
                username=claims.get("name") or f"user_{user_id}",
                email=claims.get("email"),
                avatar_url=claims.get("picture"),
            )
            session.add(user)
            session.commit()
        return user


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


class RepoInfo(BaseModel):
    repo_name: str
    summary: str
    language: str | None
    files_processed: int
    chunks_created: int
    ingested_at: datetime
    source_url: str


class DeleteRepoResponse(BaseModel):
    repo_name: str
    deleted: bool


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


class ModuleEdge(BaseModel):
    source: str
    target: str
    call_count: int


class CodebaseMapResponse(BaseModel):
    entry_points: list[str]
    module_edges: list[ModuleEdge]
    reading_order: list[str]


class ArchitectureNode(BaseModel):
    id: str
    label: str
    tier: str
    centrality: float


class ArchitectureEdge(BaseModel):
    source: str
    target: str
    weight: int


class ArchitectureGraphResponse(BaseModel):
    nodes: list[ArchitectureNode]
    edges: list[ArchitectureEdge]


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


@app.get("/auth/whoami")
def whoami(request: Request, jwt_auth: NextAuthJWT = Depends(get_jwt_auth)) -> dict:
    return jwt_auth(request)


@app.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest, current_user: User = Depends(get_current_user)) -> IngestResponse:
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
    language = detect_primary_language(source_files)

    chunks = []
    for source_file in source_files:
        chunks.extend(
            build_chunks(source_file.path, source_file.relative_path, source_file.last_modified)
        )

    collection = get_collection(current_user.id, request.repo_name)
    upsert_chunks(collection, chunks)

    call_graph = build_call_graph(source_files)
    save_call_graph(current_user.id, request.repo_name, call_graph)

    chunk_dicts = [_chunk_to_dict(chunk) for chunk in chunks]
    summary = generate_repo_summary(chunk_dicts)
    save_summary(
        current_user.id,
        request.repo_name,
        request.source,
        summary,
        files_processed=len(source_files),
        chunks_created=len(chunks),
        language=language,
    )

    return IngestResponse(
        repo_name=request.repo_name,
        files_processed=len(source_files),
        chunks_created=len(chunks),
        time_seconds=time.monotonic() - start,
        summary=summary,
    )


@app.get("/summary/{repo_name}", response_model=SummaryResponse)
def get_repo_summary(repo_name: str, current_user: User = Depends(get_current_user)) -> SummaryResponse:
    stored = get_summary(current_user.id, repo_name)

    if stored is None:
        raise HTTPException(status_code=404, detail=f"Repo '{repo_name}' not found.")

    return SummaryResponse(repo_name=repo_name, summary=stored["summary"])


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, current_user: User = Depends(get_current_user)) -> QueryResponse:
    stored = get_summary(current_user.id, request.repo_name)
    if stored is None:
        raise HTTPException(status_code=404, detail=f"Repo '{request.repo_name}' not found.")

    collection = get_collection(current_user.id, request.repo_name)

    if collection.count() == 0:
        raise HTTPException(status_code=404, detail=f"Repo '{request.repo_name}' not found.")

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

    github_url = github_url_for(stored["source"]) if stored else None

    return QueryResponse(**answer, github_url=github_url)


@app.get("/repos", response_model=list[RepoInfo])
def list_ingested_repos(current_user: User = Depends(get_current_user)) -> list[RepoInfo]:
    return [RepoInfo(**repo) for repo in list_repos(current_user.id)]


@app.delete("/repos/{repo_name}", response_model=DeleteRepoResponse)
def delete_ingested_repo(repo_name: str, current_user: User = Depends(get_current_user)) -> DeleteRepoResponse:
    deleted = delete_repo(current_user.id, repo_name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Repo '{repo_name}' not found.")

    delete_collection(current_user.id, repo_name)
    delete_call_graph(current_user.id, repo_name)

    return DeleteRepoResponse(repo_name=repo_name, deleted=True)


@app.get("/codebase-map/{repo_name}", response_model=CodebaseMapResponse)
def codebase_map(repo_name: str, current_user: User = Depends(get_current_user)) -> CodebaseMapResponse:
    graph = load_call_graph(current_user.id, repo_name)

    if graph is None:
        raise HTTPException(status_code=404, detail=f"Repo '{repo_name}' not found.")

    entry_points = detect_entry_points(graph)
    module_graph = build_module_graph(graph)
    reading_order = suggest_reading_order(module_graph, entry_points)

    module_edges = [
        ModuleEdge(source=source, target=target, call_count=data["call_count"])
        for source, target, data in module_graph.edges(data=True)
    ]

    return CodebaseMapResponse(
        entry_points=entry_points,
        module_edges=module_edges,
        reading_order=reading_order,
    )


@app.get("/architecture-graph/{repo_name}", response_model=ArchitectureGraphResponse)
def architecture_graph(repo_name: str, current_user: User = Depends(get_current_user)) -> ArchitectureGraphResponse:
    graph = load_call_graph(current_user.id, repo_name)

    if graph is None:
        raise HTTPException(status_code=404, detail=f"Repo '{repo_name}' not found.")

    module_graph = build_module_graph(graph)

    if module_graph.number_of_nodes() == 0:
        raise HTTPException(status_code=404, detail=f"No module graph available for repo '{repo_name}'.")

    entry_files = detect_module_level_entry_points(module_graph)

    pagerank = nx.pagerank(module_graph, weight="call_count")
    scores = list(pagerank.values())
    min_score, max_score = min(scores), max(scores)
    score_range = max_score - min_score

    normalized = {
        node: (score - min_score) / score_range if score_range > 0 else 0.0
        for node, score in pagerank.items()
    }

    non_entry_scores = sorted(
        (score for node, score in normalized.items() if node not in entry_files), reverse=True
    )
    core_threshold = (
        non_entry_scores[max(0, math.ceil(len(non_entry_scores) * 0.4) - 1)]
        if non_entry_scores
        else None
    )

    nodes = []
    for node in module_graph.nodes:
        if node in entry_files:
            tier = "entry_point"
        elif core_threshold is not None and normalized[node] >= core_threshold:
            tier = "core_service"
        else:
            tier = "utility"

        nodes.append(
            ArchitectureNode(id=node, label=Path(node).name, tier=tier, centrality=normalized[node])
        )

    edges = [
        ArchitectureEdge(source=source, target=target, weight=data["call_count"])
        for source, target, data in module_graph.edges(data=True)
    ]

    return ArchitectureGraphResponse(nodes=nodes, edges=edges)


@app.post("/diagram", response_model=DiagramResponse | AmbiguousDiagramResponse)
def diagram(request: DiagramRequest, current_user: User = Depends(get_current_user)) -> DiagramResponse | AmbiguousDiagramResponse:
    graph = load_call_graph(current_user.id, request.repo_name)

    if graph is None:
        raise HTTPException(status_code=404, detail=f"Repo '{request.repo_name}' not found.")

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
