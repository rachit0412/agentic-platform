"""
LangChain LLM & Embeddings wrappers — multi-provider support.

Providers:
  1. Ollama       — local models (llama3, mistral, deepseek-r1, etc.)
  2. Azure OpenAI — via API key (gpt-4o, gpt-4o-mini, gpt-35-turbo, etc.)
  3. OpenAI       — via API key (gpt-4o, gpt-4o-mini, gpt-3.5-turbo, etc.)
  4. Azure Foundry — via API key

Provides:
  get_llm(provider, model, temperature) → ChatOllama | AzureChatOpenAI | ChatOpenAI
  get_embeddings(provider)              → OllamaEmbeddings | AzureOpenAIEmbeddings | OpenAIEmbeddings
  list_available_models()               → list of model dicts
  get_active_model()                    → current provider + model + embedding info
"""

import json
import logging
import os

logger = logging.getLogger("agent-service.llm")

# ── Persistent config (survives container restarts) ─────────────────────────
_CONFIG_PATH = os.path.join(os.getenv("MEMORY_DIR", "/data"), "llm-config.json")


def _load_persisted_config() -> dict:
    """Load saved provider/model from disk, if present."""
    try:
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_persisted_config(provider: str, model: str) -> None:
    """Write active provider/model to disk so restarts keep the selection."""
    try:
        os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
        with open(_CONFIG_PATH, "w") as f:
            json.dump({"provider": provider, "model": model}, f)
    except OSError as exc:
        logger.warning("Could not persist LLM config: %s", exc)


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
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"
)

# ── OpenAI config ───────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# ── Azure AI Foundry config ─────────────────────────────────────────────────
AZURE_FOUNDRY_API_KEY = os.getenv("AZURE_FOUNDRY_API_KEY", "")
AZURE_FOUNDRY_ENDPOINT = os.getenv("AZURE_FOUNDRY_ENDPOINT", "")
AZURE_FOUNDRY_MODEL = os.getenv("AZURE_FOUNDRY_MODEL", "")  # default model
AZURE_FOUNDRY_MODELS = [
    m.strip() for m in os.getenv("AZURE_FOUNDRY_MODELS", "").split(",") if m.strip()
]  # all deployments
AZURE_FOUNDRY_API_VERSION = os.getenv("AZURE_FOUNDRY_API_VERSION", "2024-10-21")
AZURE_FOUNDRY_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_FOUNDRY_EMBEDDING_DEPLOYMENT", "")

# ── Embedding provider override (defaults to LLM provider) ─────────────────
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "")  # "" = follow LLM provider


def _is_real_key(value: str) -> bool:
    """Return False for empty or obvious placeholder API keys."""
    if not value or not value.strip():
        return False
    low = value.lower()
    return not any(
        w in low for w in ("your-", "placeholder", "if-needed", "change", "xxx", "todo")
    )


# ── Active model state ──────────────────────────────────────────────────────
# Persisted config (written by set_active_model) takes precedence over env vars.
_persisted = _load_persisted_config()
_active_provider = _persisted.get(
    "provider",
    os.getenv("LLM_PROVIDER", "ollama"),
)  # "ollama" | "azure-openai" | "openai" | "azure-foundry"
_env_default_model = (
    AZURE_OPENAI_DEPLOYMENT
    if _active_provider == "azure-openai"
    else (
        OPENAI_MODEL
        if _active_provider == "openai"
        else (
            AZURE_FOUNDRY_MODEL if _active_provider == "azure-foundry" else OLLAMA_MODEL
        )
    )
)
_active_model = _persisted.get("model", _env_default_model)
_llm = None
_embeddings = None
_embedding_provider = None  # tracks which provider the current embeddings use


def get_llm(
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    max_completion_tokens: int | None = None,
):
    """Return a chat LLM instance for the given provider."""
    global _llm, _active_provider, _active_model

    p = provider or _active_provider
    t = temperature if temperature is not None else OLLAMA_TEMPERATURE
    tp = top_p if top_p is not None else 1.0
    mct = max_completion_tokens or 2048
    rebuild = (
        _llm is None
        or provider is not None
        or model is not None
        or temperature is not None
        or top_p is not None
        or max_completion_tokens is not None
    )

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
            logger.info(
                "AzureChatOpenAI initialised: deployment=%s endpoint=%s temp=%.2f top_p=%.2f",
                m,
                AZURE_OPENAI_ENDPOINT,
                t,
                tp,
            )
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
            logger.info(
                "ChatOpenAI initialised: model=%s temp=%.2f top_p=%.2f", m, t, tp
            )
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
            logger.info(
                "AzureChatOpenAI (Foundry) initialised: model=%s endpoint=%s temp=%.2f top_p=%.2f",
                m,
                AZURE_FOUNDRY_ENDPOINT,
                t,
                tp,
            )
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
            logger.info(
                "ChatOllama initialised: model=%s base=%s temp=%.2f top_p=%.2f",
                m,
                OLLAMA_BASE_URL,
                t,
                tp,
            )

    return _llm


def get_embeddings(provider: str | None = None):
    """Return an embeddings instance for the given provider.

    Provider resolution order:
      1. Explicit `provider` argument
      2. EMBEDDING_PROVIDER env var
      3. Active LLM provider (_active_provider)

    Supported: ollama, azure-openai, openai, azure-foundry
    """
    global _embeddings, _embedding_provider

    p = provider or EMBEDDING_PROVIDER or _active_provider

    # Reuse cached instance if provider unchanged
    if _embeddings is not None and _embedding_provider == p:
        return _embeddings

    if p == "azure-openai":
        if not _is_real_key(AZURE_OPENAI_API_KEY) or not AZURE_OPENAI_ENDPOINT:
            logger.warning(
                "Azure OpenAI embeddings requested but no valid key/endpoint — falling back to Ollama"
            )
            return _build_ollama_embeddings()
        from langchain_openai import AzureOpenAIEmbeddings

        _embeddings = AzureOpenAIEmbeddings(
            azure_deployment=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
        )
        _embedding_provider = "azure-openai"
        logger.info(
            "AzureOpenAIEmbeddings initialised: deployment=%s",
            AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        )

    elif p == "openai":
        if not _is_real_key(OPENAI_API_KEY):
            logger.warning(
                "OpenAI embeddings requested but no valid key — falling back to Ollama"
            )
            return _build_ollama_embeddings()
        from langchain_openai import OpenAIEmbeddings

        _embeddings = OpenAIEmbeddings(
            model=OPENAI_EMBEDDING_MODEL,
            api_key=OPENAI_API_KEY,
        )
        _embedding_provider = "openai"
        logger.info("OpenAIEmbeddings initialised: model=%s", OPENAI_EMBEDDING_MODEL)

    elif p == "azure-foundry":
        if not _is_real_key(AZURE_FOUNDRY_API_KEY) or not AZURE_FOUNDRY_ENDPOINT:
            logger.warning(
                "Azure Foundry embeddings requested but no valid key/endpoint — falling back to Ollama"
            )
            return _build_ollama_embeddings()
        embed_deployment = (
            AZURE_FOUNDRY_EMBEDDING_DEPLOYMENT or AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        )
        from langchain_openai import AzureOpenAIEmbeddings

        _embeddings = AzureOpenAIEmbeddings(
            azure_deployment=embed_deployment,
            azure_endpoint=AZURE_FOUNDRY_ENDPOINT,
            api_key=AZURE_FOUNDRY_API_KEY,
            api_version=AZURE_FOUNDRY_API_VERSION,
        )
        _embedding_provider = "azure-foundry"
        logger.info(
            "AzureOpenAIEmbeddings (Foundry) initialised: deployment=%s",
            embed_deployment,
        )

    else:
        return _build_ollama_embeddings()

    return _embeddings


def _build_ollama_embeddings():
    """Build Ollama embeddings (default fallback)."""
    global _embeddings, _embedding_provider
    from langchain_ollama import OllamaEmbeddings

    _embeddings = OllamaEmbeddings(
        model=OLLAMA_EMBED_MODEL,
        base_url=OLLAMA_BASE_URL,
    )
    _embedding_provider = "ollama"
    logger.info("OllamaEmbeddings initialised: model=%s", OLLAMA_EMBED_MODEL)
    return _embeddings


def list_available_embedding_providers() -> list[str]:
    """Return embedding provider names that have valid credentials configured."""
    available = ["ollama"]  # always available
    if _is_real_key(OPENAI_API_KEY):
        available.append("openai")
    if _is_real_key(AZURE_OPENAI_API_KEY) and AZURE_OPENAI_ENDPOINT:
        available.append("azure-openai")
    if _is_real_key(AZURE_FOUNDRY_API_KEY) and AZURE_FOUNDRY_ENDPOINT:
        available.append("azure-foundry")
    return available


def list_available_models() -> list[dict]:
    """List all available models across all configured providers."""
    models = []

    # Model capability metadata: which features each model/provider supports
    # temperature_supported=False means the API only allows default (1.0)
    _MODEL_CAPS = {
        "gpt-5-nano": {
            "temperature": False,
            "top_p": True,
            "max_tokens": 16384,
            "streaming": True,
        },
        "gpt-4o": {
            "temperature": True,
            "top_p": True,
            "max_tokens": 128000,
            "streaming": True,
        },
        "gpt-4o-mini": {
            "temperature": True,
            "top_p": True,
            "max_tokens": 128000,
            "streaming": True,
        },
        "gpt-4.1": {
            "temperature": True,
            "top_p": True,
            "max_tokens": 32768,
            "streaming": True,
        },
        "gpt-4.1-mini": {
            "temperature": True,
            "top_p": True,
            "max_tokens": 32768,
            "streaming": True,
        },
        "gpt-4.1-nano": {
            "temperature": True,
            "top_p": True,
            "max_tokens": 32768,
            "streaming": True,
        },
        "gpt-3.5-turbo": {
            "temperature": True,
            "top_p": True,
            "max_tokens": 16384,
            "streaming": True,
        },
    }
    _OLLAMA_CAPS = {
        "temperature": True,
        "top_p": True,
        "max_tokens": 32768,
        "streaming": True,
    }
    _DEFAULT_CAPS = {
        "temperature": True,
        "top_p": True,
        "max_tokens": 4096,
        "streaming": True,
    }

    def _caps(model_name: str, provider: str) -> dict:
        m = model_name.lower()
        for key, caps in _MODEL_CAPS.items():
            if key in m:
                return caps
        if provider == "ollama":
            return _OLLAMA_CAPS
        return _DEFAULT_CAPS

    # Known embedding-only model patterns (excluded from LLM list)
    _EMBEDDING_PATTERNS = {
        "nomic-embed",
        "mxbai-embed",
        "all-minilm",
        "snowflake-arctic-embed",
        "bge-",
        "e5-",
        "gte-",
        "embed",
        "sentence-transformers",
    }

    def _is_embedding_model(name: str) -> bool:
        n = name.lower()
        return any(p in n for p in _EMBEDDING_PATTERNS)

    # ── Ollama models ───────────────────────────────────────────────────
    try:
        import httpx

        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            for m in data.get("models", []):
                name = m.get("name", "").split(":")[0]
                if _is_embedding_model(name):
                    continue
                models.append(
                    {
                        "provider": "ollama",
                        "model": name,
                        "full_name": m.get("name", name),
                        "size": m.get("size", 0),
                        "active": _active_provider == "ollama"
                        and _active_model == name,
                        "capabilities": _caps(name, "ollama"),
                        "cost_per_1k_input": 0.0,
                        "cost_per_1k_output": 0.0,
                    }
                )
    except Exception as e:
        logger.warning("Failed to list Ollama models: %s", e)

    # ── Azure OpenAI models ─────────────────────────────────────────────
    if _is_real_key(AZURE_OPENAI_API_KEY) and AZURE_OPENAI_ENDPOINT:
        azure_models = [
            {"model": AZURE_OPENAI_DEPLOYMENT, "description": "Configured deployment"},
        ]
        for am in azure_models:
            models.append(
                {
                    "provider": "azure-openai",
                    "model": am["model"],
                    "full_name": am["model"],
                    "size": 0,
                    "active": _active_provider == "azure-openai"
                    and _active_model == am["model"],
                    "capabilities": _caps(am["model"], "azure-openai"),
                    "cost_per_1k_input": 0.0,
                    "cost_per_1k_output": 0.0,
                }
            )

    # ── OpenAI models ───────────────────────────────────────────────────
    if _is_real_key(OPENAI_API_KEY):
        models.append(
            {
                "provider": "openai",
                "model": OPENAI_MODEL,
                "full_name": OPENAI_MODEL,
                "size": 0,
                "active": _active_provider == "openai"
                and _active_model == OPENAI_MODEL,
                "capabilities": _caps(OPENAI_MODEL, "openai"),
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
            }
        )

    # ── Azure Foundry models ────────────────────────────────────────────
    if _is_real_key(AZURE_FOUNDRY_API_KEY) and AZURE_FOUNDRY_ENDPOINT:
        foundry_list = (
            AZURE_FOUNDRY_MODELS
            if AZURE_FOUNDRY_MODELS
            else ([AZURE_FOUNDRY_MODEL] if AZURE_FOUNDRY_MODEL else [])
        )
        seen = set()
        for fm in foundry_list:
            if fm and fm not in seen:
                seen.add(fm)
                models.append(
                    {
                        "provider": "azure-foundry",
                        "model": fm,
                        "full_name": fm,
                        "size": 0,
                        "active": _active_provider == "azure-foundry"
                        and _active_model == fm,
                        "capabilities": _caps(fm, "azure-foundry"),
                        "cost_per_1k_input": 0.0,
                        "cost_per_1k_output": 0.0,
                    }
                )

    return models


def get_active_model() -> dict:
    """Return the currently active provider, model, and embedding info."""
    embed_p = _embedding_provider or EMBEDDING_PROVIDER or _active_provider
    embed_models = {
        "ollama": OLLAMA_EMBED_MODEL,
        "azure-openai": AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        "openai": OPENAI_EMBEDDING_MODEL,
        "azure-foundry": AZURE_FOUNDRY_EMBEDDING_DEPLOYMENT
        or AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    }
    return {
        "provider": _active_provider,
        "model": _active_model,
        "embedding_provider": embed_p,
        "embedding_model": embed_models.get(embed_p, OLLAMA_EMBED_MODEL),
    }


def set_active_model(
    provider: str,
    model: str,
    temperature: float | None = None,
    top_p: float | None = None,
    max_completion_tokens: int | None = None,
):
    """Switch the active LLM provider and model."""
    old_provider = _active_provider
    get_llm(
        provider=provider,
        model=model,
        temperature=temperature,
        top_p=top_p,
        max_completion_tokens=max_completion_tokens,
    )
    # Persist so the choice survives container restarts
    _save_persisted_config(_active_provider, _active_model)
    # Reset embeddings if provider changed and no explicit EMBEDDING_PROVIDER override
    global _embeddings, _embedding_provider
    if (
        not EMBEDDING_PROVIDER
        and _embedding_provider
        and _embedding_provider != provider
    ):
        _embeddings = None
        _embedding_provider = None
        logger.info(
            "Embedding provider reset — will follow new LLM provider: %s", provider
        )
    return get_active_model()


def set_embedding_model(provider: str, model: str):
    """Switch the embedding provider and model independently of the LLM."""
    global _embeddings, _embedding_provider, OLLAMA_EMBED_MODEL
    global OPENAI_EMBEDDING_MODEL, AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    global AZURE_FOUNDRY_EMBEDDING_DEPLOYMENT

    model_map = {
        "ollama": "OLLAMA_EMBED_MODEL",
        "openai": "OPENAI_EMBEDDING_MODEL",
        "azure-openai": "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
        "azure-foundry": "AZURE_FOUNDRY_EMBEDDING_DEPLOYMENT",
    }
    if provider not in model_map:
        raise ValueError(f"Unknown embedding provider: {provider}")

    # Update the module-level model variable for the provider
    if provider == "ollama":
        OLLAMA_EMBED_MODEL = model
    elif provider == "openai":
        OPENAI_EMBEDDING_MODEL = model
    elif provider == "azure-openai":
        AZURE_OPENAI_EMBEDDING_DEPLOYMENT = model
    elif provider == "azure-foundry":
        AZURE_FOUNDRY_EMBEDDING_DEPLOYMENT = model

    # Force re-initialisation on next call
    _embeddings = None
    _embedding_provider = provider

    # Re-init now to validate
    get_embeddings(provider)
    logger.info("Embedding switched to %s / %s", provider, model)
    return get_active_model()
