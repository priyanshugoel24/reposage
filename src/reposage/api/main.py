from datetime import datetime
from functools import lru_cache
from pathlib import Path
import json
import math
import os
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
from reposage.indexing.summary_store import (
    delete_repo,
    get_summary,
    get_tour_steps,
    github_url_for,
    list_repos,
    save_summary,
    save_tour_steps,
)
from reposage.indexing.vectorstore import delete_collection, get_collection, query_collection, upsert_chunks
from reposage.rag.synthesize import generate_repo_summary, synthesize_answer
from reposage.rag.tour import generate_tour_narration
from reposage.graph.call_graph import (
    build_call_graph,
    save_call_graph,
    load_call_graph,
    delete_call_graph,
    get_transitive_callers,
)
from reposage.graph.flow_diagram import trace_subgraph, generate_flow_diagram
from reposage.graph.codebase_map import (
    detect_entry_points,
    detect_module_level_entry_points,
    build_module_graph,
    order_tour_stops,
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
    # Render sets RENDER=true automatically in deployed services; use it to mirror the
    # frontend's NODE_ENV-gated secure-cookie switch, so the expected cookie name
    # ("__Secure-authjs.session-token" in production, "authjs.session-token" locally)
    # always matches what the frontend actually sets.
    return NextAuthJWT(secure_cookie=os.environ.get("RENDER") == "true")


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
    function_count: int
    functions: list[str]


class ArchitectureEdge(BaseModel):
    source: str
    target: str
    weight: int


class ArchitectureGraphResponse(BaseModel):
    nodes: list[ArchitectureNode]
    edges: list[ArchitectureEdge]


class BlastRadiusNode(BaseModel):
    id: str
    label: str
    distance: int | None = None
    centrality: float | None = None
    function_count: int | None = None
    functions: list[str] | None = None


class BlastRadiusEdge(BaseModel):
    source: str
    target: str
    weight: int


class BlastRadiusResponse(BaseModel):
    ambiguous: bool
    nodes: list[BlastRadiusNode]
    edges: list[BlastRadiusEdge]
    qualified_name: str


class AmbiguousBlastRadiusResponse(BaseModel):
    ambiguous: bool
    candidates: list[str]


class TourStep(BaseModel):
    module_id: str
    label: str
    tier: str
    title: str
    narration: str
    key_functions: list[str]
    function_count: int


class TourResponse(BaseModel):
    steps: list[TourStep]


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

    # save_call_graph writes to the repos row, so the row must already exist (save_summary above).
    save_call_graph(current_user.id, request.repo_name, call_graph)

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


class ArchitectureData:
    def __init__(
        self,
        graph: nx.DiGraph,
        module_graph: nx.DiGraph,
        entry_files: set[str],
        centrality: dict[str, float],
        tier_by_node: dict[str, str],
        functions_by_file: dict[str, list[str]],
    ) -> None:
        self.graph = graph
        self.module_graph = module_graph
        self.entry_files = entry_files
        self.centrality = centrality
        self.tier_by_node = tier_by_node
        self.functions_by_file = functions_by_file


def _build_architecture_data(repo_name: str, current_user: User) -> ArchitectureData:
    """Load the call graph and compute the module graph, entry points, normalized
    PageRank centrality, and tiers once, shared by /architecture-graph and /tour.
    Raises HTTPException(404) if the repo or module graph isn't available."""
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

    tier_by_node: dict[str, str] = {}
    for node in module_graph.nodes:
        if node in entry_files:
            tier_by_node[node] = "entry_point"
        elif core_threshold is not None and normalized[node] >= core_threshold:
            tier_by_node[node] = "core_service"
        else:
            tier_by_node[node] = "utility"

    functions_by_file: dict[str, list[str]] = {}
    for _, data in graph.nodes(data=True):
        functions_by_file.setdefault(data["file"], []).append(data["name"])
    for node in functions_by_file:
        functions_by_file[node].sort()

    return ArchitectureData(
        graph=graph,
        module_graph=module_graph,
        entry_files=entry_files,
        centrality=normalized,
        tier_by_node=tier_by_node,
        functions_by_file=functions_by_file,
    )


@app.get("/architecture-graph/{repo_name}", response_model=ArchitectureGraphResponse)
def architecture_graph(repo_name: str, current_user: User = Depends(get_current_user)) -> ArchitectureGraphResponse:
    data = _build_architecture_data(repo_name, current_user)

    nodes = []
    for node in data.module_graph.nodes:
        module_functions = data.functions_by_file.get(node, [])

        nodes.append(
            ArchitectureNode(
                id=node,
                label=Path(node).name,
                tier=data.tier_by_node[node],
                centrality=data.centrality[node],
                function_count=len(module_functions),
                functions=module_functions[:15],
            )
        )

    edges = [
        ArchitectureEdge(source=source, target=target, weight=edge_data["call_count"])
        for source, target, edge_data in data.module_graph.edges(data=True)
    ]

    return ArchitectureGraphResponse(nodes=nodes, edges=edges)


@app.get("/tour/{repo_name}", response_model=TourResponse)
def tour(repo_name: str, current_user: User = Depends(get_current_user)) -> TourResponse:
    cached = get_tour_steps(current_user.id, repo_name)
    if cached is not None:
        return TourResponse(steps=[TourStep(**step) for step in json.loads(cached)])

    data = _build_architecture_data(repo_name, current_user)

    ordered_module_ids = order_tour_stops(data.module_graph, data.entry_files, data.centrality)

    dependency_counts = {node: data.module_graph.out_degree(node) for node in data.module_graph.nodes}
    dependent_counts = {node: data.module_graph.in_degree(node) for node in data.module_graph.nodes}

    modules_for_narration = [
        {
            "file_path": module_id,
            "tier": data.tier_by_node[module_id],
            "functions": data.functions_by_file.get(module_id, []),
            "function_count": len(data.functions_by_file.get(module_id, [])),
            "dependency_count": dependency_counts[module_id],
            "dependent_count": dependent_counts[module_id],
        }
        for module_id in ordered_module_ids
    ]

    narrations = generate_tour_narration(modules_for_narration)

    steps = [
        TourStep(
            module_id=module["file_path"],
            label=Path(module["file_path"]).name,
            tier=module["tier"],
            title=narration["title"],
            narration=narration["narration"],
            key_functions=module["functions"][:15],
            function_count=module["function_count"],
        )
        for module, narration in zip(modules_for_narration, narrations)
    ]

    save_tour_steps(
        current_user.id, repo_name, json.dumps([step.model_dump() for step in steps])
    )

    return TourResponse(steps=steps)


def _resolve_function_name(graph: nx.DiGraph, function_name: str) -> str | list[str]:
    """Resolve a plain function name to a qualified name in the call graph.

    Returns the qualified name if resolution is unambiguous, or a list of
    candidate qualified names if the function name is ambiguous. Raises
    HTTPException(404) if no function with that name exists."""

    if function_name in graph.nodes:
        return function_name

    candidates = [
        qname for qname, data in graph.nodes(data=True)
        if data.get("name") == function_name
    ]

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"No function named '{function_name}' found in this repo.",
        )
    if len(candidates) == 1:
        return candidates[0]
    return candidates


@app.post("/diagram", response_model=DiagramResponse | AmbiguousDiagramResponse)
def diagram(request: DiagramRequest, current_user: User = Depends(get_current_user)) -> DiagramResponse | AmbiguousDiagramResponse:
    graph = load_call_graph(current_user.id, request.repo_name)

    if graph is None:
        raise HTTPException(status_code=404, detail=f"Repo '{request.repo_name}' not found.")

    resolved = _resolve_function_name(graph, request.function_name)
    if isinstance(resolved, list):
        return AmbiguousDiagramResponse(ambiguous=True, candidates=resolved)
    qualified_name = resolved

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


@app.get("/blast-radius/{repo_name}", response_model=BlastRadiusResponse | AmbiguousBlastRadiusResponse)
def blast_radius(
    repo_name: str,
    function_name: str,
    max_depth: int = 3,
    current_user: User = Depends(get_current_user),
) -> BlastRadiusResponse | AmbiguousBlastRadiusResponse:
    graph = load_call_graph(current_user.id, repo_name)

    if graph is None:
        raise HTTPException(status_code=404, detail=f"Repo '{repo_name}' not found.")

    resolved = _resolve_function_name(graph, function_name)
    if isinstance(resolved, list):
        return AmbiguousBlastRadiusResponse(ambiguous=True, candidates=resolved)
    qualified_name = resolved

    subgraph = get_transitive_callers(graph, qualified_name, max_depth=max_depth)

    distances = nx.single_source_shortest_path_length(subgraph.reverse(copy=False), qualified_name)

    nodes = [
        BlastRadiusNode(
            id=node,
            label=data.get("name", Path(node.split("::")[0]).name),
            distance=distances.get(node),
        )
        for node, data in subgraph.nodes(data=True)
    ]

    edges = [
        BlastRadiusEdge(source=source, target=target, weight=1)
        for source, target in subgraph.edges()
    ]

    return BlastRadiusResponse(
        ambiguous=False,
        nodes=nodes,
        edges=edges,
        qualified_name=qualified_name,
    )
