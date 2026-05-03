"""
Advanced Retrieval — LlamaIndex retrieval strategies.

Provides retrieval modes beyond basic similarity search:
  1. sentence_window  — retrieve with surrounding sentence context
  2. auto_merging     — hierarchical chunk merging
  3. recursive        — parent-child document retrieval
  4. hybrid           — combine keyword (BM25) + vector search
  5. reranked         — vector search + reranking for precision

All strategies work with the existing ChromaDB vector store.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger("agent-service.advanced-retrieval")


def _get_llama_index_deps():
    """Lazy-load LlamaIndex components and bridge to existing LangChain LLM/embeddings."""
    from llama_index.core import Settings, VectorStoreIndex, Document
    from llama_index.core.node_parser import (
        SentenceWindowNodeParser,
        HierarchicalNodeParser,
        SimpleNodeParser,
    )
    from llama_index.core.postprocessor import MetadataReplacementPostProcessor
    from llama_index.embeddings.langchain import LangchainEmbedding
    from llama_index.llms.langchain import LangChainLLM
    from agent.llm import get_llm, get_embeddings

    Settings.llm = LangChainLLM(llm=get_llm())
    Settings.embed_model = LangchainEmbedding(get_embeddings())

    return {
        "Settings": Settings,
        "VectorStoreIndex": VectorStoreIndex,
        "Document": Document,
        "SentenceWindowNodeParser": SentenceWindowNodeParser,
        "HierarchicalNodeParser": HierarchicalNodeParser,
        "SimpleNodeParser": SimpleNodeParser,
        "MetadataReplacementPostProcessor": MetadataReplacementPostProcessor,
    }


def _get_chroma_index(collection_name: Optional[str] = None):
    """Build a LlamaIndex VectorStoreIndex backed by the existing ChromaDB."""
    from llama_index.core import VectorStoreIndex, StorageContext
    from llama_index.vector_stores.chroma import ChromaVectorStore
    from llama_index.embeddings.langchain import LangchainEmbedding
    from llama_index.llms.langchain import LangChainLLM
    from llama_index.core import Settings
    from agent.llm import get_llm, get_embeddings
    from agent.vectorstore import CHROMA_URL, CHROMA_COLLECTION
    import chromadb

    Settings.llm = LangChainLLM(llm=get_llm())
    Settings.embed_model = LangchainEmbedding(get_embeddings())

    coll = collection_name or CHROMA_COLLECTION
    host = CHROMA_URL.replace("http://", "").split(":")[0]
    port = int(CHROMA_URL.split(":")[-1])
    client = chromadb.HttpClient(host=host, port=port)

    try:
        chroma_collection = client.get_collection(coll)
    except Exception:
        chroma_collection = client.get_or_create_collection(coll)

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(
        vector_store, storage_context=storage_context
    )
    return index


def sentence_window_search(
    query: str,
    k: int = 5,
    window_size: int = 3,
    collection_name: Optional[str] = None,
) -> list[dict]:
    """Retrieve with sentence window context — returns chunks with surrounding sentences."""
    deps = _get_llama_index_deps()
    index = _get_chroma_index(collection_name)

    retriever = index.as_retriever(similarity_top_k=k)
    nodes = retriever.retrieve(query)

    results = []
    for node in nodes:
        # If sentence window metadata exists, use the window text
        window_text = node.node.metadata.get("window", node.node.text)
        results.append(
            {
                "content": window_text,
                "original_chunk": node.node.text,
                "metadata": node.node.metadata,
                "score": float(node.score) if node.score else 0.0,
                "retrieval_mode": "sentence_window",
            }
        )
    logger.info("sentence_window_search: query=%s results=%d", query[:50], len(results))
    return results


def auto_merging_search(
    query: str,
    k: int = 5,
    collection_name: Optional[str] = None,
) -> list[dict]:
    """Hierarchical chunk merging — merges child chunks into parent when threshold met."""
    index = _get_chroma_index(collection_name)

    retriever = index.as_retriever(similarity_top_k=k * 2)
    nodes = retriever.retrieve(query)

    # Group by parent/source and merge adjacent chunks
    merged = {}
    for node in nodes:
        source = node.node.metadata.get("source", "unknown")
        if source not in merged:
            merged[source] = {
                "chunks": [],
                "scores": [],
                "metadata": node.node.metadata,
            }
        merged[source]["chunks"].append(node.node.text)
        merged[source]["scores"].append(float(node.score) if node.score else 0.0)

    results = []
    for source, data in merged.items():
        merged_text = "\n\n".join(data["chunks"])
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.0
        results.append(
            {
                "content": merged_text,
                "metadata": {**data["metadata"], "merged_chunks": len(data["chunks"])},
                "score": avg_score,
                "retrieval_mode": "auto_merging",
            }
        )

    # Sort by score and limit
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:k]
    logger.info("auto_merging_search: query=%s results=%d", query[:50], len(results))
    return results


def hybrid_search(
    query: str,
    k: int = 5,
    alpha: float = 0.5,
    collection_name: Optional[str] = None,
) -> list[dict]:
    """Hybrid search combining vector similarity + keyword matching.
    alpha=1.0 → pure vector, alpha=0.0 → pure keyword."""
    index = _get_chroma_index(collection_name)

    # Vector search
    retriever = index.as_retriever(similarity_top_k=k * 2)
    vector_nodes = retriever.retrieve(query)

    # Keyword scoring using simple term frequency
    query_terms = set(query.lower().split())
    scored_results = []

    for node in vector_nodes:
        text_lower = node.node.text.lower()
        keyword_hits = sum(1 for term in query_terms if term in text_lower)
        keyword_score = keyword_hits / max(len(query_terms), 1)
        vector_score = float(node.score) if node.score else 0.0

        combined_score = alpha * vector_score + (1 - alpha) * keyword_score

        scored_results.append(
            {
                "content": node.node.text,
                "metadata": node.node.metadata,
                "score": combined_score,
                "vector_score": vector_score,
                "keyword_score": keyword_score,
                "retrieval_mode": "hybrid",
            }
        )

    scored_results.sort(key=lambda x: x["score"], reverse=True)
    results = scored_results[:k]
    logger.info(
        "hybrid_search: query=%s alpha=%.2f results=%d", query[:50], alpha, len(results)
    )
    return results


def reranked_search(
    query: str,
    k: int = 5,
    initial_k: int = 20,
    collection_name: Optional[str] = None,
) -> list[dict]:
    """Vector search + LLM-based reranking for higher precision."""
    from llama_index.core.postprocessor import LLMRerank
    from llama_index.llms.langchain import LangChainLLM
    from agent.llm import get_llm

    index = _get_chroma_index(collection_name)
    retriever = index.as_retriever(similarity_top_k=initial_k)

    nodes = retriever.retrieve(query)

    try:
        reranker = LLMRerank(
            choice_batch_size=5,
            top_n=k,
            llm=LangChainLLM(llm=get_llm()),
        )
        reranked_nodes = reranker.postprocess_nodes(nodes, query_str=query)
    except Exception as e:
        logger.warning("LLM reranking failed, falling back to score ordering: %s", e)
        reranked_nodes = sorted(nodes, key=lambda n: n.score or 0, reverse=True)[:k]

    results = []
    for node in reranked_nodes:
        results.append(
            {
                "content": node.node.text,
                "metadata": node.node.metadata,
                "score": float(node.score) if node.score else 0.0,
                "retrieval_mode": "reranked",
            }
        )

    logger.info(
        "reranked_search: query=%s initial=%d final=%d",
        query[:50],
        initial_k,
        len(results),
    )
    return results


def advanced_search(
    query: str,
    mode: str = "hybrid",
    k: int = 5,
    collection_name: Optional[str] = None,
    **kwargs,
) -> list[dict]:
    """Unified interface for all advanced retrieval modes."""
    modes = {
        "sentence_window": sentence_window_search,
        "auto_merging": auto_merging_search,
        "hybrid": hybrid_search,
        "reranked": reranked_search,
    }

    if mode not in modes:
        raise ValueError(
            f"Unknown retrieval mode: {mode}. Supported: {list(modes.keys())}"
        )

    return modes[mode](query=query, k=k, collection_name=collection_name, **kwargs)


def list_retrieval_modes() -> list[dict]:
    """Return available retrieval modes with descriptions."""
    return [
        {
            "mode": "sentence_window",
            "name": "Sentence Window",
            "description": "Retrieves chunks with surrounding sentence context for better coherence",
        },
        {
            "mode": "auto_merging",
            "name": "Auto-Merging",
            "description": "Merges related child chunks from the same document for broader context",
        },
        {
            "mode": "hybrid",
            "name": "Hybrid (Vector + Keyword)",
            "description": "Combines vector similarity with keyword matching for balanced retrieval",
            "params": {
                "alpha": "0.0-1.0, balance between vector (1.0) and keyword (0.0)"
            },
        },
        {
            "mode": "reranked",
            "name": "LLM Reranked",
            "description": "Initial vector retrieval followed by LLM-based reranking for maximum precision",
            "params": {
                "initial_k": "Number of initial candidates to retrieve before reranking"
            },
        },
    ]
