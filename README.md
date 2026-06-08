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

## How It Works

```
Document
   │
   ▼
document_loader.py  ── extract text, clean whitespace/tabs
   │
   ▼
chunker.py          ── split on paragraphs → merge to ~1500 chars with 200-char overlap
   │
   ▼
embedder.py         ── embed each chunk via gemini-embedding-001 (3072 dims)
   │
   ▼
vector_store.py     ── upsert into ChromaDB (cosine similarity index)


Query
   │
   ▼
embedder.py         ── embed the user question
   │
   ▼
vector_store.py     ── retrieve top-k most similar chunks
   │
   ▼
rag_engine.py       ── build augmented prompt → call gemini-2.5-flash → return answer
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
