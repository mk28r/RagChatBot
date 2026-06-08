# Production RAG

A local Retrieval-Augmented Generation (RAG) system powered by **Google Gemini** and **ChromaDB**. Upload any document, ask questions in plain English, and get answers grounded in your document's content — with source citations.

---

## Features

- **Multi-format ingestion** — PDF, TXT, DOCX, CSV, HTML
- **Paragraph-aware chunking** — respects natural text boundaries for higher retrieval quality
- **Gemini embeddings** — `gemini-embedding-001` (3072-dim vectors)
- **ChromaDB vector store** — persistent on-disk cosine-similarity search
- **Gemini 2.5 Flash** — fast, accurate answer generation
- **Streamlit UI** — chat interface + chunk browser, no coding needed
- **CLI** — headless ingest and chat for scripting

---

## Project Structure

```
.
├── app.py               # Streamlit web UI
├── main.py              # CLI entry point
├── document_loader.py   # File parsing + text cleaning
├── chunker.py           # Paragraph-aware sliding-window chunker
├── embedder.py          # Gemini embedding calls
├── vector_store.py      # ChromaDB store + retrieval
├── rag_engine.py        # Full RAG pipeline (embed → retrieve → generate)
├── req.txt              # Python dependencies
└── chroma_db/           # Auto-created persistent vector store
```

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd "Production Rag"
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r req.txt
pip install google-genai streamlit
```

### 3. Set your Gemini API key

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_api_key_here
```

Get a free key at [https://aistudio.google.com](https://aistudio.google.com).

---

## Usage

### Streamlit UI (recommended)

```bash
streamlit run app.py
```

- **Sidebar → Upload documents** — drag and drop a file, click **Ingest**
- **💬 Chat** — ask questions, see answers with source citations
- **🔍 Browse Chunks** — inspect the raw stored chunks, filter by document or keyword

### CLI

**Ingest a document:**
```bash
python3 main.py ingest path/to/file.pdf
```

**Ingest multiple files at once:**
```bash
python3 main.py ingest report.pdf notes.txt data.csv
```

**Start the chat:**
```bash
python3 main.py chat
```

> Documents are ingested once and persisted in `chroma_db/`. Re-running ingest on the same file is safe — chunks are upserted, not duplicated.

---

## System Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACES                            │
│                                                                     │
│   ┌─────────────────────────┐     ┌─────────────────────────┐      │
│   │     Streamlit UI        │     │      CLI (main.py)      │      │
│   │  app.py                 │     │  python3 main.py        │      │
│   │  • Upload & ingest      │     │  ingest <file>          │      │
│   │  • Chat interface       │     │  chat                   │      │
│   │  • Browse chunks        │     │                         │      │
│   └────────────┬────────────┘     └────────────┬────────────┘      │
└────────────────┼─────────────────────────────── ┼───────────────────┘
                 │                                 │
        ┌────────▼─────────────────────────────────▼────────┐
        │                    CORE PIPELINE                   │
        │                                                    │
        │   INGEST PATH                  QUERY PATH          │
        │   ──────────                  ───────────          │
        │   document_loader.py          rag_engine.py        │
        │   chunker.py                  embedder.py          │
        │   embedder.py                 vector_store.py      │
        │   vector_store.py             gemini-2.5-flash     │
        └────────────────────┬───────────────────────────────┘
                             │
        ┌────────────────────▼───────────────────────────────┐
        │                  STORAGE LAYER                     │
        │                                                    │
        │   ChromaDB  (chroma_db/ on disk)                   │
        │   • Collection: "documents"                        │
        │   • Distance metric: cosine                        │
        │   • Stores: embeddings, raw text, metadata         │
        └────────────────────────────────────────────────────┘
                             │
        ┌────────────────────▼───────────────────────────────┐
        │               EXTERNAL SERVICES                    │
        │                                                    │
        │   Google Gemini API                                │
        │   • gemini-embedding-001  →  3072-dim vectors      │
        │   • gemini-2.5-flash      →  answer generation     │
        └────────────────────────────────────────────────────┘
```

---

## How It Works

### Ingestion Pipeline

When you upload a document, it goes through 4 sequential stages:

```
┌──────────────┐
│  Raw File    │  PDF / TXT / DOCX / CSV / HTML
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Stage 1 · document_loader.py · Parse & Clean        │
│                                                      │
│  • PDF  → pypdf extraction_mode="layout"             │
│           (preserves word order, avoids tab noise)   │
│  • All  → _clean():                                  │
│           replace \t with space                      │
│           collapse multiple spaces                   │
│           normalize blank lines                      │
│                                                      │
│  Output: clean plain-text string                     │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Stage 2 · chunker.py · Paragraph-Aware Splitting    │
│                                                      │
│  1. Split text on blank lines → paragraphs[]         │
│  2. Merge paragraphs until chunk ≤ 1500 chars        │
│  3. On overflow → flush chunk, carry 200-char        │
│     overlap into next chunk                          │
│  4. Oversized single paragraph → sentence splitter   │
│                                                      │
│  Output: list of chunk dicts                         │
│  { chunk_id, text, source, chunk_index, token_count }│
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Stage 3 · embedder.py · Vectorise                   │
│                                                      │
│  For each chunk:                                     │
│  gemini-embedding-001 (task: RETRIEVAL_DOCUMENT)     │
│  → 3072-dimensional float vector                     │
│                                                      │
│  Output: chunk dicts + "embedding" field             │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Stage 4 · vector_store.py · Persist                 │
│                                                      │
│  ChromaDB collection.upsert(                         │
│    ids        = chunk_id[]                           │
│    embeddings = vector[]                             │
│    documents  = text[]                               │
│    metadatas  = { source, chunk_index, token_count } │
│  )                                                   │
│  Safe to re-run — upsert deduplicates by chunk_id    │
└──────────────────────────────────────────────────────┘
```

---

### Query Pipeline

When you ask a question:

```
┌──────────────┐
│  User Query  │  "How do I reduce silly mistakes?"
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Step 1 · embedder.py · Embed Question               │
│                                                      │
│  gemini-embedding-001 (task: RETRIEVAL_QUERY)        │
│  → 3072-dim query vector                             │
│                                                      │
│  Note: different task_type than indexing —           │
│  optimised for asymmetric retrieval                  │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Step 2 · vector_store.py · Retrieve top-k           │
│                                                      │
│  ChromaDB cosine similarity search                   │
│  Returns top-k chunks ranked by similarity score     │
│  Score = 1 - cosine_distance  (range 0 → 1)         │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Step 3 · rag_engine.py · Build Augmented Prompt     │
│                                                      │
│  ┌─ SYSTEM PROMPT ──────────────────────────────┐   │
│  │ You are a precise technical assistant.        │   │
│  │ Use ONLY the context below to answer.         │   │
│  │ Quote directly. Cite source file.             │   │
│  └───────────────────────────────────────────── ┘   │
│  ┌─ CONTEXT (top-k chunks) ─────────────────────┐   │
│  │ [Source: file.pdf, chunk 3]                   │   │
│  │ <chunk text>                                  │   │
│  │ ---                                           │   │
│  │ [Source: file.pdf, chunk 7]                   │   │
│  │ <chunk text>  ...                             │   │
│  └───────────────────────────────────────────── ┘   │
│  ┌─ QUESTION ────────────────────────────────────┐   │
│  │ How do I reduce silly mistakes?               │   │
│  └───────────────────────────────────────────── ┘   │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Step 4 · Gemini 2.5 Flash · Generate Answer         │
│                                                      │
│  Returns: { answer, retrieved_chunks, sources }      │
└──────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│   Response   │  Answer + collapsible source citations
└──────────────┘
```

---

## Low-Level Design (LLD)

### Module Responsibilities

| Module | Responsibility | Key Functions |
|---|---|---|
| `document_loader.py` | Parse file → clean text string | `load_document(file_path)` → `{text, source, doc_type, hash}` |
| `chunker.py` | Split text into overlapping chunks | `chunk_text(text, source)` → `list[chunk_dict]` |
| `embedder.py` | Call Gemini embedding API | `embed_chunks(chunks)`, `embed_query(query)` |
| `vector_store.py` | Persist and search chunks | `store_chunks(chunks)`, `retrieve(embedding, top_k)` |
| `rag_engine.py` | Orchestrate full query pipeline | `query(question, top_k)` → `{answer, sources, chunks}` |
| `app.py` | Streamlit UI | Ingest via upload, chat, browse chunks |
| `main.py` | CLI entry point | `ingest(file)`, `chat_loop()` |

### Data Flow & Schemas

```
document_loader  →  chunker
──────────────────────────────────────────────────────
Input:   file path (str)
Output:  {
           text:     str        # cleaned full document text
           source:   str        # original filename
           doc_type: str        # "pdf" | "txt" | "docx" …
           hash:     str        # md5 for deduplication
         }


chunker  →  embedder
──────────────────────────────────────────────────────
Input:   text (str), source (str)
Output:  list of {
           chunk_id:    str     # "{source}__chunk_{idx}"
           text:        str     # chunk content (≤ 1500 chars)
           source:      str     # original filename
           chunk_index: int     # position in document
           token_count: int     # estimated token count
         }


embedder  →  vector_store
──────────────────────────────────────────────────────
Input:   list of chunk dicts (above)
Output:  same dicts + embedding: list[float]  # 3072 dims


vector_store.retrieve  →  rag_engine
──────────────────────────────────────────────────────
Input:   query_embedding: list[float], top_k: int
Output:  list of {
           text:        str
           source:      str
           chunk_index: int
           score:       float   # cosine similarity 0–1
         }


rag_engine.query  →  UI / CLI
──────────────────────────────────────────────────────
Input:   user_question: str, top_k: int
Output:  {
           question:         str
           answer:           str
           retrieved_chunks: list[chunk]
           sources:          list[str]
         }
```

### ChromaDB Collection Schema

```
Collection name : "documents"
Distance metric : cosine

Per record:
  id        →  "{filename}__chunk_{n}"   (unique, used for upsert dedup)
  embedding →  float[3072]
  document  →  raw chunk text
  metadata  →  {
                 source:      str   # filename
                 chunk_index: int
                 token_count: int
               }
```

### Chunking Algorithm Detail

```
chunk_text(text, source, max_chars=1500, overlap_chars=200)

1.  paragraphs = split(text, on="\n\n")     # blank-line boundaries

2.  for each paragraph:
      candidate = current + "\n\n" + paragraph

      if len(candidate) ≤ max_chars:
          current = candidate                # keep accumulating

      else:
          if current not empty:
              emit chunk(current)
              current = current[-200:] + paragraph   # overlap carry
          else:
              # paragraph alone exceeds limit → sentence split
              emit hard_split(paragraph)
              current = ""

3.  if current not empty:
        emit chunk(current)                  # flush final chunk
```

---

## Configuration

| Parameter | Location | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | `.env` | — | Your Google Gemini API key |
| `EMBED_MODEL` | `embedder.py` | `models/gemini-embedding-001` | Embedding model |
| `max_chars` | `chunker.py` | `1500` | Max characters per chunk |
| `overlap_chars` | `chunker.py` | `200` | Overlap between chunks |
| `top_k` | Streamlit slider / CLI arg | `5` | Chunks retrieved per query |
| Generation model | `rag_engine.py` | `models/gemini-2.5-flash` | LLM for answer generation |

---

## Clearing the vector store

**From the UI:** Sidebar → **🗑️ All chunks**

**From the terminal:**
```bash
rm -rf chroma_db/
```

Then re-ingest your documents.

---

## Supported File Types

| Extension | Parser |
|---|---|
| `.pdf` | `pypdf` (layout-aware extraction) |
| `.txt` | built-in |
| `.docx` | `python-docx` |
| `.html` / `.htm` | `beautifulsoup4` |
| `.csv` | built-in `csv` module |
