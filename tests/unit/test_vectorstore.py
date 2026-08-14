"""Unit tests for vectorstore module."""

import sys
import types
import pytest
from unittest.mock import patch, MagicMock

# Pre-create mock modules that may not be installed locally
for _mod_name in ("langchain_chroma", "chromadb"):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = types.ModuleType(_mod_name)
        if _mod_name == "langchain_chroma":
            sys.modules[_mod_name].Chroma = MagicMock()
        if _mod_name == "chromadb":
            sys.modules[_mod_name].HttpClient = MagicMock()


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the vectorstore cache between tests."""
    import agent.vectorstore as vs_mod

    vs_mod._vectorstores.clear()
    yield
    vs_mod._vectorstores.clear()


@pytest.fixture(autouse=True)
def mock_embeddings():
    """Mock get_embeddings so tests don't need a running Ollama."""
    with patch("agent.llm.get_embeddings") as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture(autouse=True)
def mock_chroma():
    """Mock Chroma client so tests don't need a running ChromaDB."""
    # Mock the raw chromadb collection (used by get_collection_stats, delete_document)
    mock_raw_collection = MagicMock()
    mock_raw_collection.count.return_value = 10
    mock_raw_collection.get.return_value = {
        "ids": ["id1", "id2"],
        "metadatas": [{"source": "a.txt"}, {"source": "b.txt"}],
    }
    mock_raw_client = MagicMock()
    mock_raw_client.get_collection.return_value = mock_raw_collection

    # Mock the LangChain Chroma wrapper (used by get_vectorstore, delete_document)
    chroma_instance = MagicMock()
    chroma_instance._collection = mock_raw_collection
    chroma_instance.get.return_value = {
        "ids": ["id1", "id2"],
        "metadatas": [{"source": "a.txt"}, {"source": "b.txt"}],
    }
    chroma_instance.similarity_search_with_score.return_value = [
        (MagicMock(page_content="hello", metadata={"source": "a.txt"}), 0.9),
    ]

    with patch(
        "langchain_chroma.Chroma", return_value=chroma_instance
    ) as mock_cls, patch("chromadb.HttpClient", return_value=mock_raw_client):
        yield mock_cls


class TestGetVectorstore:
    def test_returns_chroma_instance(self, mock_chroma):
        from agent.vectorstore import get_vectorstore

        vs = get_vectorstore()
        assert vs is not None


class TestCollectionStats:
    def test_stats_returns_count_and_sources(self, mock_chroma):
        from agent.vectorstore import get_collection_stats

        stats = get_collection_stats()
        assert stats["total_chunks"] == 10
        assert stats["unique_documents"] == 2


class TestSearchSimilar:
    def test_search_returns_results(self, mock_chroma):
        from agent.vectorstore import search_similar

        results = search_similar("hello", k=3)
        assert len(results) == 1
        assert results[0]["content"] == "hello"
        assert results[0]["score"] == 0.9


class TestListDocuments:
    def test_list_returns_sources(self, mock_chroma):
        from agent.vectorstore import list_documents

        docs = list_documents()
        sources = [d["source"] for d in docs]
        assert "a.txt" in sources
        assert "b.txt" in sources


class TestDeleteDocument:
    def test_delete_calls_chroma(self, mock_chroma):
        from agent.vectorstore import delete_document

        # The delete_document function gets the _collection from get_vectorstore()
        # and calls collection.get(where=...) then collection.delete(ids=...)
        result = delete_document("a.txt")
        assert result["source"] == "a.txt"
