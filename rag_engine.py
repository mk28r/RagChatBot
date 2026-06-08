# rag_engine.py
import os
from google import genai
from dotenv import load_dotenv
from embedder     import embed_query
from vector_store import retrieve

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """You are a precise technical assistant. Use ONLY the context below to answer.
Rules:
- Quote or paraphrase directly from the context; do not add outside knowledge.
- If the answer is not in the context, say exactly: "I don't have enough information to answer that."
- Structure your answer clearly (use bullet points or numbered steps when helpful).
- End with: Source: <filename>"""

def query(user_question: str, top_k: int = 5, verbose: bool = False) -> dict:
    """
    Full RAG pipeline:
    1. Embed the question
    2. Retrieve top-k relevant chunks
    3. Build augmented prompt
    4. Generate answer with Gemini
    """
    # ── Step 1: Embed query ──────────────────────────────────────────────
    q_embedding = embed_query(user_question)

    # ── Step 2: Retrieve relevant chunks ────────────────────────────────
    chunks = retrieve(q_embedding, top_k=top_k)

    if verbose:
        print(f"\n[Retrieval] Top {top_k} chunks:")
        for i, c in enumerate(chunks):
            print(f"  [{i+1}] score={c['score']} source={c['source']}")
            print(f"       {c['text'][:120]}...")

    # ── Step 3: Build augmented prompt ──────────────────────────────────
    context_block = "\n\n---\n\n".join(
        f"[Source: {c['source']}, chunk {c['chunk_index']}]\n{c['text']}"
        for c in chunks
    )

    prompt = f"""{SYSTEM_PROMPT}

=== CONTEXT ===
{context_block}

=== QUESTION ===
{user_question}

=== ANSWER ==="""

    # ── Step 4: LLM generation ──────────────────────────────────────────
    response = client.models.generate_content(model="models/gemini-2.5-flash", contents=prompt)
    answer   = response.text

    return {
        "question":       user_question,
        "answer":         answer,
        "retrieved_chunks": chunks,
        "sources":        list({c["source"] for c in chunks}),
    }
