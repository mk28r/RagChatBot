# vector_store.py
import chromadb
from chromadb.config import Settings

# Persistent on-disk store (production: replace with Pinecone / pgvector)
client     = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name     = "documents",
    # cosine distance works better than L2 for text embeddings
    metadata = {"hnsw:space": "cosine"},
)

def store_chunks(chunks: list[dict]) -> None:
    """Upsert chunks into ChromaDB (safe to re-run; won't duplicate)."""
    collection.upsert(
        ids        = [c["chunk_id"] for c in chunks],
        embeddings = [c["embedding"] for c in chunks],
        documents  = [c["text"] for c in chunks],
        metadatas  = [{
            "source":      c["source"],
            "chunk_index": c["chunk_index"],
            "token_count": c["token_count"],
        } for c in chunks],
    )
    print(f"[VectorStore] Stored {len(chunks)} chunks")

def retrieve(query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """Retrieve top-k most similar chunks to the query."""
    results = collection.query(
        query_embeddings = [query_embedding],
        n_results        = top_k,
        include          = ["documents", "metadatas", "distances"],
    )
    retrieved = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        retrieved.append({
            "text":       doc,
            "source":     meta["source"],
            "chunk_index": meta["chunk_index"],
            "score":      round(1 - dist, 4),  # cosine similarity
        })
    return retrieved