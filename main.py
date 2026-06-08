# main.py  ← run this file
from document_loader import load_document
from chunker         import chunk_text
from embedder        import embed_chunks
from vector_store    import store_chunks
from rag_engine      import query

def ingest(file_path: str) -> None:
    """Complete ingestion pipeline for any document."""
    print(f"\n{'='*50}")
    print(f"Ingesting: {file_path}")
    print('='*50)

    # Stage 1 – Load
    doc    = load_document(file_path)
    print(f"[Load]   Extracted {len(doc['text'])} characters from {doc['source']}")

    # Stage 2 – Chunk
    chunks = chunk_text(doc["text"], source=doc["source"])

    # Stage 3 – Embed
    chunks = embed_chunks(chunks)

    # Stage 4 – Store
    store_chunks(chunks)
    print(f"[Done]   {doc['source']} is now searchable!")

def chat_loop() -> None:
    """Interactive Q&A loop over ingested documents."""
    print("\n💬 RAG Chat — type 'quit' to exit\n")
    while True:
        q = input("You: ").strip()
        if q.lower() in ("quit", "exit", "q"):
            break
        result = query(q, top_k=5, verbose=True)
        print(f"\nAssistant: {result['answer']}")
        print(f"Sources: {', '.join(result['sources'])}\n")

if __name__ == "__main__":
    import sys

    # python main.py ingest report.pdf
    # python main.py ingest data.csv notes.txt  ← multiple files
    # python main.py chat
    mode = sys.argv[1] if len(sys.argv) > 1 else "chat"

    if mode == "ingest":
        for f in sys.argv[2:]:
            ingest(f)
    elif mode == "chat":
        chat_loop()
    else:
        print("Usage: python main.py ingest <files...>  OR  python main.py chat")