import streamlit as st
import tempfile, os
from pathlib import Path

from document_loader import load_document
from chunker         import chunk_text
from embedder        import embed_chunks
from vector_store    import store_chunks, collection
from rag_engine      import query

st.set_page_config(page_title="RAG Chat", page_icon="📚", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📚 RAG Chat")

    page = st.radio("Navigate", ["💬 Chat", "🔍 Browse Chunks"], label_visibility="collapsed")

    st.divider()
    st.subheader("Upload documents")
    uploaded = st.file_uploader(
        "Drag & drop files",
        type=["pdf", "txt", "docx", "csv", "html"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if uploaded and st.button("Ingest", type="primary"):
        for file in uploaded:
            with st.spinner(f"Ingesting {file.name}…"):
                suffix = Path(file.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(file.read())
                    tmp_path = tmp.name
                try:
                    doc           = load_document(tmp_path)
                    doc["source"] = file.name
                    chunks        = chunk_text(doc["text"], source=file.name)
                    chunks        = embed_chunks(chunks)
                    store_chunks(chunks)
                    st.success(f"✅ {file.name} ({len(chunks)} chunks)")
                except Exception as e:
                    st.error(f"❌ {file.name}: {e}")
                finally:
                    os.unlink(tmp_path)

    st.divider()
    st.subheader("Ingested documents")
    try:
        all_meta = collection.get(include=["metadatas"])["metadatas"]
        sources  = sorted({m["source"] for m in all_meta}) if all_meta else []
        for s in sources:
            st.markdown(f"- {s}")
        if not sources:
            st.caption("No documents yet.")
    except Exception:
        st.caption("No documents yet.")

    st.divider()
    top_k = st.slider("Chunks to retrieve (top-k)", 1, 10, 5)

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col_b:
        if st.button("🗑️ All chunks", use_container_width=True):
            try:
                collection.delete(where={"chunk_index": {"$gte": 0}})
                st.success("Cleared.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

# ── Page: Chat ────────────────────────────────────────────────────────────────
if page == "💬 Chat":
    st.title("💬 RAG Chat")

    # Render history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("Sources"):
                    for chunk in msg["sources"]:
                        st.caption(
                            f"**{chunk['source']}** · chunk {chunk['chunk_index']} "
                            f"· score {chunk['score']}"
                        )
                        st.markdown(f"> {chunk['text'][:300]}…")

    # Pinned input — must be at module level, NOT inside any container
    if prompt := st.chat_input("Ask something about your documents…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    result = query(prompt, top_k=top_k)
                    answer = result["answer"]
                    chunks = result["retrieved_chunks"]
                except Exception as e:
                    answer = f"Error: {e}"
                    chunks = []

            st.markdown(answer)
            if chunks:
                with st.expander("Sources"):
                    for chunk in chunks:
                        st.caption(
                            f"**{chunk['source']}** · chunk {chunk['chunk_index']} "
                            f"· score {chunk['score']}"
                        )
                        st.markdown(f"> {chunk['text'][:300]}…")

        st.session_state.messages.append({
            "role":    "assistant",
            "content": answer,
            "sources": chunks,
        })

# ── Page: Browse Chunks ───────────────────────────────────────────────────────
elif page == "🔍 Browse Chunks":
    st.title("🔍 Browse Chunks")
    try:
        data  = collection.get(include=["documents", "metadatas"])
        docs  = data["documents"]
        metas = data["metadatas"]

        if not docs:
            st.info("No chunks stored yet. Ingest a document first.")
        else:
            sources = sorted({m["source"] for m in metas})
            col1, col2 = st.columns([2, 3])
            with col1:
                chosen = st.selectbox("Filter by document", ["All"] + sources)
            with col2:
                search = st.text_input("Search in chunks", placeholder="keyword…")

            rows = list(zip(docs, metas))
            if chosen != "All":
                rows = [(d, m) for d, m in rows if m["source"] == chosen]
            if search:
                rows = [(d, m) for d, m in rows if search.lower() in d.lower()]

            st.caption(f"Showing **{len(rows)}** chunk(s)")
            for doc, meta in rows:
                with st.expander(
                    f"**{meta['source']}** · chunk {meta['chunk_index']} "
                    f"· ~{meta['token_count']} tokens"
                ):
                    st.text(doc)
    except Exception as e:
        st.error(f"Could not load chunks: {e}")
