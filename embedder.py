# embedder.py
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

EMBED_MODEL = "models/gemini-embedding-001"

def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Adds 'embedding' (768-dim vector) to each chunk dict.
    Uses RETRIEVAL_DOCUMENT task type for indexing.
    """
    for chunk in chunks:
        resp = client.models.embed_content(
            model   = EMBED_MODEL,
            contents = chunk["text"],
            config  = types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        chunk["embedding"] = resp.embeddings[0].values

    print(f"[Embedder] Embedded {len(chunks)} chunks (dim={len(chunks[0]['embedding'])})")
    return chunks

def embed_query(query: str) -> list[float]:
    """Embed a user query with RETRIEVAL_QUERY task type."""
    resp = client.models.embed_content(
        model    = EMBED_MODEL,
        contents = query,
        config   = types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return resp.embeddings[0].values