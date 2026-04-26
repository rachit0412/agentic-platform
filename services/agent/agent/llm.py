"""
LangChain LLM & Embeddings wrappers — multi-provider support.

Providers:
  1. Ollama   — local models (llama3, mistral, phi3, codellama, etc.)
  2. Azure OpenAI — via API key (gpt-4o, gpt-4o-mini, gpt-35-turbo, etc.)

Provides:
  get_llm(provider, model, temperature) → ChatOllama | AzureChatOpenAI
  get_embeddings()                      → OllamaEmbeddings
  list_available_models()               → list of model dicts
  get_active_model()                    → current provider + model info
"""
import os
import logging

logger = logging.getLogger("agent-service.llm")

# ── Ollama config ───────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))

# ── Azure OpenAI config ────────────────────────────────────────────────────
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

# ── Active model state ──────────────────────────────────────────────────────
_active_provider = os.getenv("LLM_PROVIDER", "ollama")  # "ollama" | "azure-openai"
_active_model = OLLAMA_MODEL if _active_provider == "ollama" else AZURE_OPENAI_DEPLOYMENT
_llm = None
_embeddings = None


def get_llm(provider: str | None = None, model: str | None = None, temperature: float | None = None):
    """Return a chat LLM instance for the given provider."""
    global _llm, _active_provider, _active_model

    p = provider or _active_provider
    t = temperature if temperature is not None else OLLAMA_TEMPERATURE
    rebuild = _llm is None or provider is not None or model is not None or temperature is not None

    if p == "azure-openai":
        m = model or AZURE_OPENAI_DEPLOYMENT
        if rebuild:
            if not AZURE_OPENAI_API_KEY or not AZURE_OPENAI_ENDPOINT:
                raise ValueError(
                    "Azure OpenAI requires AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT env vars"
                )
            from langchain_openai import AzureChatOpenAI
            _llm = AzureChatOpenAI(
                azure_deployment=m,
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_key=AZURE_OPENAI_API_KEY,
                api_version=AZURE_OPENAI_API_VERSION,
                temperature=t,
                max_tokens=2048,
            )
            _active_provider = "azure-openai"
            _active_model = m
            logger.info("AzureChatOpenAI initialised: deployment=%s endpoint=%s temp=%.2f",
                        m, AZURE_OPENAI_ENDPOINT, t)
    else:
        m = model or OLLAMA_MODEL
        if rebuild:
            from langchain_ollama import ChatOllama
            _llm = ChatOllama(
                model=m,
                base_url=OLLAMA_BASE_URL,
                temperature=t,
                num_predict=2048,
            )
            _active_provider = "ollama"
            _active_model = m
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


def list_available_models() -> list[dict]:
    """List all available models across all configured providers."""
    models = []

    # ── Ollama models ───────────────────────────────────────────────────
    try:
        import httpx
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            for m in data.get("models", []):
                name = m.get("name", "").split(":")[0]
                models.append({
                    "provider": "ollama",
                    "model": name,
                    "full_name": m.get("name", name),
                    "size": m.get("size", 0),
                    "active": _active_provider == "ollama" and _active_model == name,
                })
    except Exception as e:
        logger.warning("Failed to list Ollama models: %s", e)

    # ── Azure OpenAI models ─────────────────────────────────────────────
    if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
        azure_models = [
            {"model": AZURE_OPENAI_DEPLOYMENT, "description": "Configured deployment"},
        ]
        for am in azure_models:
            models.append({
                "provider": "azure-openai",
                "model": am["model"],
                "full_name": am["model"],
                "size": 0,
                "active": _active_provider == "azure-openai" and _active_model == am["model"],
            })

    return models


def get_active_model() -> dict:
    """Return the currently active provider and model."""
    return {
        "provider": _active_provider,
        "model": _active_model,
    }


def set_active_model(provider: str, model: str, temperature: float | None = None):
    """Switch the active LLM provider and model."""
    get_llm(provider=provider, model=model, temperature=temperature)
    return get_active_model()
