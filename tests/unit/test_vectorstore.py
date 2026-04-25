"""Unit tests for vectorstore module."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def mock_embeddings():
    """Mock OllamaEmbeddings so tests don't need a running Ollama."""
    with patch("agent.vectorstore.get_embeddings") as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture(autouse=True)
def mock_chroma():
    """Mock Chroma client so tests don't need a running ChromaDB."""
    with patch("agent.vectorstore.Chroma") as mock:
        instance = MagicMock()
        instance._collection.count.return_value = 10
        instance.get.return_value = {"metadatas": [{"source": "a.txt"}, {"source": "b.txt"}]}
        instance.similarity_search_with_score.return_value = [
            (MagicMock(page_content="hello", metadata={"source": "a.txt"}), 0.9),
        ]
        mock.return_value = instance
        yield mock


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
        assert "a.txt" in docs
        assert "b.txt" in docs


class TestDeleteDocument:
    def test_delete_calls_chroma(self, mock_chroma):
        from agent.vectorstore import delete_document
        mock_chroma.return_value.get.return_value = {"ids": ["id1", "id2"]}
        delete_document("a.txt")
        mock_chroma.return_value.delete.assert_called_once()
