import chromadb
from chromadb.utils import embedding_functions
from chromadb import EmbeddingFunction
from chromadb.api.types import Embeddable
from typing import cast

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(path=".chroma")
collection = client.get_or_create_collection(
    name="sanity_check",
    embedding_function=cast(EmbeddingFunction[Embeddable], embedding_fn),
)

collection.upsert(
    ids = ["a", "b"],
    documents = ["def add(x, y) : return x + y", "def send_email(to, subject) : ...."],
    metadatas = [{"name" : "add"}, {"name" : "send_email"}],
)

results = collection.query(query_texts=["a function that sums two numbers"], n_results = 1)

metadatas = results["metadatas"]
if metadatas is not None:
    print(metadatas[0])

