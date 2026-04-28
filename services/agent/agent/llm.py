"""
LangChain LLM & Embeddings wrappers — multi-provider support.

Providers:
  1. Ollama       — local models (llama3, mistral, deepseek-r1, etc.)
  2. Azure OpenAI — via API key (gpt-4o, gpt-4o-mini, gpt-35-turbo, etc.)
  3. OpenAI       — via API key (gpt-4o, gpt-4o-mini, gpt-3.5-turbo, etc.)

Provides:
  get_llm(provider, model, temperature) → ChatOllama | AzureChatOpenAI | ChatOpenAI
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

# ── OpenAI config ───────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ── Azure AI Foundry config ─────────────────────────────────────────────────
AZURE_FOUNDRY_API_KEY = os.getenv("AZURE_FOUNDRY_API_KEY", "")
AZURE_FOUNDRY_ENDPOINT = os.getenv("AZURE_FOUNDRY_ENDPOINT", "")
AZURE_FOUNDRY_MODEL = os.getenv("AZURE_FOUNDRY_MODEL", "")  # default model
AZURE_FOUNDRY_MODELS = [m.strip() for m in os.getenv("AZURE_FOUNDRY_MODELS", "").split(",") if m.strip()]  # all deployments
AZURE_FOUNDRY_API_VERSION = os.getenv("AZURE_FOUNDRY_API_VERSION", "2024-10-21")


def _is_real_key(value: str) -> bool:
    """Return False for empty or obvious placeholder API keys."""
    if not value or not value.strip():
        return False
    low = value.lower()
    return not any(w in low for w in ("your-", "placeholder", "if-needed", "change", "xxx", "todo"))

# ── Active model state ──────────────────────────────────────────────────────
_active_provider = os.getenv("LLM_PROVIDER", "ollama")  # "ollama" | "azure-openai" | "openai" | "azure-foundry"
_active_model = (
    AZURE_OPENAI_DEPLOYMENT if _active_provider == "azure-openai"
    else OPENAI_MODEL if _active_provider == "openai"
    else AZURE_FOUNDRY_MODEL if _active_provider == "azure-foundry"
    else OLLAMA_MODEL
)
_llm = None
_embeddings = None


def get_llm(provider: str | None = None, model: str | None = None, temperature: float | None = None, top_p: float | None = None, max_completion_tokens: int | None = None):
    """Return a chat LLM instance for the given provider."""
    global _llm, _active_provider, _active_model

    p = provider or _active_provider
    t = temperature if temperature is not None else OLLAMA_TEMPERATURE
    tp = top_p if top_p is not None else 1.0
    mct = max_completion_tokens or 2048
    rebuild = _llm is None or provider is not None or model is not None or temperature is not None or top_p is not None or max_completion_tokens is not None

    if p == "azure-openai":
        m = model or AZURE_OPENAI_DEPLOYMENT
        if rebuild:
            if not _is_real_key(AZURE_OPENAI_API_KEY) or not AZURE_OPENAI_ENDPOINT:
                raise ValueError(
                    "Azure OpenAI requires a valid AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT env vars"
                )
            from langchain_openai import AzureChatOpenAI
            _llm = AzureChatOpenAI(
                azure_deployment=m,
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_key=AZURE_OPENAI_API_KEY,
                api_version=AZURE_OPENAI_API_VERSION,
                temperature=t,
                top_p=tp,
                max_tokens=mct,
                streaming=True,
                timeout=30,
                model_kwargs={"stream_options": {"include_usage": True}},
            )
            _active_provider = "azure-openai"
            _active_model = m
            logger.info("AzureChatOpenAI initialised: deployment=%s endpoint=%s temp=%.2f top_p=%.2f",
                        m, AZURE_OPENAI_ENDPOINT, t, tp)
    elif p == "openai":
        m = model or OPENAI_MODEL
        if rebuild:
            if not _is_real_key(OPENAI_API_KEY):
                raise ValueError(
                    "OpenAI requires a valid OPENAI_API_KEY env var (current value looks like a placeholder)"
                )
            from langchain_openai import ChatOpenAI
            _llm = ChatOpenAI(
                model=m,
                api_key=OPENAI_API_KEY,
                temperature=t,
                top_p=tp,
                max_tokens=mct,
                streaming=True,
                timeout=30,
                model_kwargs={"stream_options": {"include_usage": True}},
            )
            _active_provider = "openai"
            _active_model = m
            logger.info("ChatOpenAI initialised: model=%s temp=%.2f top_p=%.2f", m, t, tp)
    elif p == "azure-foundry":
        m = model or AZURE_FOUNDRY_MODEL
        if rebuild:
            if not _is_real_key(AZURE_FOUNDRY_API_KEY) or not AZURE_FOUNDRY_ENDPOINT:
                raise ValueError(
                    "Azure Foundry requires valid AZURE_FOUNDRY_API_KEY and AZURE_FOUNDRY_ENDPOINT env vars"
                )
            from langchain_openai import AzureChatOpenAI
            # gpt-5-nano and newer models require max_completion_tokens
            # (not max_tokens).  Pass via model_kwargs so LangChain doesn't
            # try to map it to the legacy parameter.
            foundry_kwargs = dict(
                azure_deployment=m,
                azure_endpoint=AZURE_FOUNDRY_ENDPOINT,
                api_key=AZURE_FOUNDRY_API_KEY,
                api_version=AZURE_FOUNDRY_API_VERSION,
                streaming=True,
                timeout=30,
                model_kwargs={
                    "max_completion_tokens": mct,
                    "stream_options": {"include_usage": True},
                },
            )
            if t != OLLAMA_TEMPERATURE:  # only send if explicitly changed
                foundry_kwargs["temperature"] = t
            if tp != 1.0:
                foundry_kwargs["top_p"] = tp
            _llm = AzureChatOpenAI(**foundry_kwargs)
            _active_provider = "azure-foundry"
            _active_model = m
            logger.info("AzureChatOpenAI (Foundry) initialised: model=%s endpoint=%s temp=%.2f top_p=%.2f",
                        m, AZURE_FOUNDRY_ENDPOINT, t, tp)
    else:
        m = model or OLLAMA_MODEL
        if rebuild:
            from langchain_ollama import ChatOllama
            _llm = ChatOllama(
                model=m,
                base_url=OLLAMA_BASE_URL,
                temperature=t,
                top_p=tp,
                num_predict=mct,
            )
            _active_provider = "ollama"
            _active_model = m
            logger.info("ChatOllama initialised: model=%s base=%s temp=%.2f top_p=%.2f", m, OLLAMA_BASE_URL, t, tp)

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
    if _is_real_key(AZURE_OPENAI_API_KEY) and AZURE_OPENAI_ENDPOINT:
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

    # ── OpenAI models ───────────────────────────────────────────────────
    if _is_real_key(OPENAI_API_KEY):
        models.append({
            "provider": "openai",
            "model": OPENAI_MODEL,
            "full_name": OPENAI_MODEL,
            "size": 0,
            "active": _active_provider == "openai" and _active_model == OPENAI_MODEL,
        })

    # ── Azure Foundry models ────────────────────────────────────────────
    if _is_real_key(AZURE_FOUNDRY_API_KEY) and AZURE_FOUNDRY_ENDPOINT:
        foundry_list = AZURE_FOUNDRY_MODELS if AZURE_FOUNDRY_MODELS else ([AZURE_FOUNDRY_MODEL] if AZURE_FOUNDRY_MODEL else [])
        seen = set()
        for fm in foundry_list:
            if fm and fm not in seen:
                seen.add(fm)
                models.append({
                    "provider": "azure-foundry",
                    "model": fm,
                    "full_name": fm,
                    "size": 0,
                    "active": _active_provider == "azure-foundry" and _active_model == fm,
                })

    return models


def get_active_model() -> dict:
    """Return the currently active provider and model."""
    return {
        "provider": _active_provider,
        "model": _active_model,
    }


def set_active_model(provider: str, model: str, temperature: float | None = None, top_p: float | None = None, max_completion_tokens: int | None = None):
    """Switch the active LLM provider and model."""
    get_llm(provider=provider, model=model, temperature=temperature, top_p=top_p, max_completion_tokens=max_completion_tokens)
    return get_active_model()
