# chunker.py
import re

def chunk_text(
    text: str,
    source: str,
    max_chars: int = 1500,   # ~375 tokens — keeps chunks focused
    overlap_chars: int = 200, # carry last ~200 chars into next chunk for context
) -> list[dict]:
    """
    Paragraph-aware sliding-window chunker.
    Splits on blank lines first so chunks never break mid-sentence,
    then merges small paragraphs until max_chars is reached.
    """
    # Split into paragraphs on one or more blank lines
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

    chunks  = []
    current = ""
    idx     = 0

    for para in paragraphs:
        candidate = (current + "\n\n" + para).strip() if current else para

        if len(candidate) <= max_chars:
            current = candidate
        else:
            # Flush current chunk
            if current:
                chunks.append(_make(current, source, idx))
                idx += 1
                # Carry tail of current chunk as overlap into next
                current = current[-overlap_chars:] + "\n\n" + para
            else:
                # Single paragraph larger than max_chars — hard-split it
                for sub in _hard_split(para, max_chars, overlap_chars):
                    chunks.append(_make(sub, source, idx))
                    idx += 1
                current = ""

    if current.strip():
        chunks.append(_make(current.strip(), source, idx))

    print(f"[Chunker] {source} → {len(chunks)} chunks")
    return chunks


def _make(text: str, source: str, idx: int) -> dict:
    return {
        "chunk_id":    f"{source}__chunk_{idx}",
        "text":        text,
        "source":      source,
        "chunk_index": idx,
        "token_count": len(text) // 4,
    }


def _hard_split(text: str, max_chars: int, overlap: int) -> list[str]:
    """Fallback: split a single oversized paragraph by sentences."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    parts, buf = [], ""
    for sent in sentences:
        if len(buf) + len(sent) + 1 <= max_chars:
            buf = (buf + " " + sent).strip()
        else:
            if buf:
                parts.append(buf)
            buf = buf[-overlap:] + " " + sent if buf else sent
    if buf:
        parts.append(buf)
    return parts
