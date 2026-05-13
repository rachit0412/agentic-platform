"""Unit tests for LLM module."""

import pytest
from unittest.mock import patch, MagicMock


class TestGetLLM:
    @patch("langchain_ollama.ChatOllama")
    def test_returns_chat_ollama(self, mock_cls):
        mock_cls.return_value = MagicMock()
        import agent.llm as mod

        mod._llm = None
        mod._active_provider = "ollama"
        llm = mod.get_llm()
        assert llm is not None
        mock_cls.assert_called_once()

    @patch("langchain_ollama.ChatOllama")
    def test_singleton(self, mock_cls):
        mock_cls.return_value = MagicMock()
        import agent.llm as mod

        mod._llm = None
        mod._active_provider = "ollama"
        llm1 = mod.get_llm()
        llm2 = mod.get_llm()
        assert llm1 is llm2
        # Only called once due to singleton
        assert mock_cls.call_count == 1


class TestGetEmbeddings:
    @patch("langchain_ollama.OllamaEmbeddings")
    def test_returns_embeddings(self, mock_cls):
        mock_cls.return_value = MagicMock()
        import agent.llm as mod

        mod._embeddings = None
        mod._embedding_provider = None
        mod._active_provider = "ollama"
        emb = mod.get_embeddings()
        assert emb is not None
        mock_cls.assert_called_once()

    @patch("langchain_ollama.OllamaEmbeddings")
    def test_singleton(self, mock_cls):
        mock_cls.return_value = MagicMock()
        import agent.llm as mod

        mod._embeddings = None
        mod._embedding_provider = None
        mod._active_provider = "ollama"
        e1 = mod.get_embeddings()
        e2 = mod.get_embeddings()
        assert e1 is e2
        assert mock_cls.call_count == 1
