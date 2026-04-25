"""
LangChain LLM & Embeddings wrappers for Ollama.

Provides:
  get_llm()        → ChatOllama instance
  get_embeddings() → OllamaEmbeddings instance (nomic-embed-text)
"""
import os
import logging

logger = logging.getLogger("agent-service.llm")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))

_llm = None
_embeddings = None


def get_llm(model: str | None = None, temperature: float | None = None):
    """Return a ChatOllama instance (singleton unless overridden)."""
    global _llm
    m = model or OLLAMA_MODEL
    t = temperature if temperature is not None else OLLAMA_TEMPERATURE

    if _llm is None or model is not None or temperature is not None:
        from langchain_ollama import ChatOllama
        _llm = ChatOllama(
            model=m,
            base_url=OLLAMA_BASE_URL,
            temperature=t,
            num_predict=2048,
        )
        logger.info("ChatOllama initialised: model=%s base=%s temp=%.2f", m, OLLAMA_BASE_URL, t)
    return _llm


def get_embeddings():
    """Return an OllamaEmbeddings instance for vector operations."""
    global _embeddings
    if _embeddings is None:
        from langchain_ollama import OllamaEmbeddings
        _embeddings = OllamaEmbeddings(
            model=OLLAMA_EMBED_MODEL,
            base_url=OLLAMA_BASE_URL,
        )
        logger.info("OllamaEmbeddings initialised: model=%s", OLLAMA_EMBED_MODEL)
    return _embeddings
