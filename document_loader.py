# document_loader.py
import os, hashlib, re
from pathlib import Path

def _clean(text: str) -> str:
    text = text.replace("\t", " ")
    text = re.sub(r" {2,}", " ", text)        # collapse multiple spaces
    text = re.sub(r" *\n *", "\n", text)      # trim spaces around newlines
    text = re.sub(r"\n{3,}", "\n\n", text)    # collapse 3+ blank lines → 1
    return text.strip()

def load_document(file_path: str) -> dict:
    """
    Supports: .txt, .pdf, .docx, .html, .csv
    Returns: { text, source, doc_type, hash }
    """
    path = Path(file_path)
    ext  = path.suffix.lower()
    text = ""

    if ext == ".txt":
        text = path.read_text(encoding="utf-8")

    elif ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        pages  = []
        for page in reader.pages:
            # extract_text with layout mode preserves word order far better
            raw = page.extract_text(extraction_mode="layout") or ""
            pages.append(raw)
        text = "\n\n".join(pages)

    elif ext == ".docx":
        from docx import Document
        doc  = Document(file_path)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    elif ext in (".html", ".htm"):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(path.read_text(), "html.parser")
        text = soup.get_text(separator="\n", strip=True)

    elif ext == ".csv":
        import csv
        rows = list(csv.reader(path.open()))
        # First row as headers, rest as data rows
        text = "\n".join(", ".join(row) for row in rows)

    else:
        raise ValueError(f"Unsupported file type: {ext}")

    text = _clean(text)
    doc_hash = hashlib.md5(text.encode()).hexdigest()

    return {
        "text":     text,
        "source":   path.name,
        "doc_type": ext.lstrip("."),
        "hash":     doc_hash,
    }