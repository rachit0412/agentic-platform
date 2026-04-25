"""
ChromaDB vector-store client for RAG operations.

Provides:
  get_vectorstore()    → Chroma client (LangChain wrapper)
  ingest_document()    → Split text into chunks and add to collection
  search_similar()     → Semantic similarity search
  get_collection_stats → Return doc/chunk counts
  delete_document()    → Remove chunks by source ID
  list_documents()     → List unique document sources
"""
import os
import logging
from typing import Optional

logger = logging.getLogger("agent-service.vectorstore")

CHROMA_URL = os.getenv("CHROMA_URL", "http://chromadb:8000")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "agentic_docs")

_vectorstore = None


def get_vectorstore():
    """Return a LangChain Chroma instance backed by the HTTP client."""
    global _vectorstore
    if _vectorstore is None:
        from langchain_chroma import Chroma
        from agent.llm import get_embeddings
        _vectorstore = Chroma(
            collection_name=CHROMA_COLLECTION,
            embedding_function=get_embeddings(),
            collection_metadata={"hnsw:space": "cosine"},
        )
        # Try HTTP client if CHROMA_URL is configured
        if CHROMA_URL:
            import chromadb
            client = chromadb.HttpClient(
                host=CHROMA_URL.replace("http://", "").split(":")[0],
                port=int(CHROMA_URL.split(":")[-1]),
            )
            _vectorstore = Chroma(
                client=client,
                collection_name=CHROMA_COLLECTION,
                embedding_function=get_embeddings(),
                collection_metadata={"hnsw:space": "cosine"},
            )
        logger.info("ChromaDB connected: %s collection=%s", CHROMA_URL, CHROMA_COLLECTION)
    return _vectorstore


def ingest_document(
    text: str,
    source: str,
    metadata: Optional[dict] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> dict:
    """Split text into chunks and add to ChromaDB. Returns stats."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)

    metadatas = []
    ids = []
    for i, chunk in enumerate(chunks):
        doc_meta = {"source": source, "chunk_index": i, "total_chunks": len(chunks)}
        if metadata:
            doc_meta.update(metadata)
        metadatas.append(doc_meta)
        ids.append(f"{source}__chunk_{i}")

    vs = get_vectorstore()
    vs.add_texts(texts=chunks, metadatas=metadatas, ids=ids)
    logger.info("Ingested document source=%s chunks=%d", source, len(chunks))

    return {"source": source, "chunks": len(chunks), "chunk_size": chunk_size}


def search_similar(query: str, k: int = 5, filter_dict: Optional[dict] = None) -> list[dict]:
    """Semantic similarity search. Returns list of {content, metadata, score}."""
    vs = get_vectorstore()
    if filter_dict:
        results = vs.similarity_search_with_score(query, k=k, filter=filter_dict)
    else:
        results = vs.similarity_search_with_score(query, k=k)

    return [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score),
        }
        for doc, score in results
    ]


def get_collection_stats() -> dict:
    """Get stats about the vector store collection."""
    try:
        vs = get_vectorstore()
        collection = vs._collection
        count = collection.count()
        # Get unique sources
        all_meta = collection.get(include=["metadatas"])
        sources = set()
        for m in (all_meta.get("metadatas") or []):
            if m and "source" in m:
                sources.add(m["source"])
        return {
            "collection": CHROMA_COLLECTION,
            "total_chunks": count,
            "unique_documents": len(sources),
            "sources": sorted(sources),
        }
    except Exception as e:
        logger.warning("Failed to get collection stats: %s", e)
        return {"collection": CHROMA_COLLECTION, "total_chunks": 0, "unique_documents": 0, "sources": [], "error": str(e)}


def delete_document(source: str) -> dict:
    """Delete all chunks for a given source document."""
    try:
        vs = get_vectorstore()
        collection = vs._collection
        # Get IDs matching this source
        results = collection.get(where={"source": source}, include=[])
        ids = results.get("ids", [])
        if ids:
            collection.delete(ids=ids)
        logger.info("Deleted document source=%s chunks=%d", source, len(ids))
        return {"source": source, "deleted_chunks": len(ids)}
    except Exception as e:
        logger.error("Failed to delete document source=%s: %s", source, e)
        return {"source": source, "deleted_chunks": 0, "error": str(e)}


def list_documents() -> list[dict]:
    """List all unique documents in the collection."""
    stats = get_collection_stats()
    return [{"source": s} for s in stats.get("sources", [])]
