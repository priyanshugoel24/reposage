import chromadb
from chromadb import EmbeddingFunction
from chromadb.api.types import Embeddable
from chromadb.utils import embedding_functions
from pathlib import Path
from reposage.indexing.chunk import Chunk
from typing import cast
import os

CHROMA_PATH = Path(os.getenv("REPOSAGE_DATA_DIR", ".")) / ".chroma"


embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2",
    
)

def get_collection(repo_name : str) :
    client = chromadb.PersistentClient(path = str(CHROMA_PATH))
    return client.get_or_create_collection(
        name = repo_name,
        embedding_function=cast(EmbeddingFunction[Embeddable], embedding_fn),
    )


def upsert_chunks(collection, chunks : list[Chunk]):
    if not chunks :
        return

    collection.upsert(
        ids = [c.chunk_id for c in chunks],
        documents = [c.source_code for c in chunks],
        metadatas = [
{
            "file_path" : c.file_path,
            "language" : c.language,
            "symbol_name" : c.symbol_name,
            "symbol_type" : c.symbol_type,
            "start_line" : c.start_line,
            "end_line" : c.end_line,
            "last_modified" : c.last_modified,}
            for c in chunks
        ],
    )

def query_collection(collection, query_text : str, n_results : int = 5) :
    return collection.query(query_texts=[query_text], n_results = n_results)