"""
LangGraph agent with ReAct loop.

Graph:
  START → reason → (tool calls?) → execute_tools → reason → … (max 5 iters) → END

Uses ChatOllama (LangChain) instead of raw HTTP.
Persists exchanges to SQLite memory.
"""

import os
import json
import logging
from typing import TypedDict, Annotated, AsyncIterator

from langgraph.graph import StateGraph, END
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)

from agent.memory import (
    get_history,
    save_message,
    get_session_summary,
    update_session_summary,
)
from agent.tools import get_all_tools, catalogue_as_text, call_tool, TOOL_CATALOGUE
from agent.llm import get_llm
from agent.llm import get_active_model as _get_active_model
from agent.observability import (
    LangfuseTrace,
    track_llm_call,
    tool_call_counter,
    agent_run_counter,
)
import re as _re

logger = logging.getLogger("agent-service.graph")

MAX_ITERATIONS = int(os.getenv("MAX_REACT_ITERATIONS", "5"))


# ── Guardrail enforcement ───────────────────────────────────────────────────

_PII_PATTERNS = {
    "email": _re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "phone": _re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": _re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": _re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
}

_INJECTION_PATTERNS = [
    "ignore previous",
    "ignore all previous",
    "disregard above",
    "disregard all",
    "new instructions",
    "override system",
    "forget everything",
    "you are now",
    "act as if",
    "ignore the above",
    "bypass",
    "jailbreak",
    "do not follow",
    "do anything now",
    "pretend you",
    "system prompt",
    "reveal your instructions",
]


def _check_guardrails_input(text: str, agent_config: dict | None = None) -> list[dict]:
    """Run enabled input guardrails. Returns list of {guardrail, status, detail}.
    If agent_config has a 'guardrails' key, only run those guardrail IDs."""
    results = []
    try:
        from agent.memory import list_guardrails

        guardrails = list_guardrails()
    except Exception:
        return results

    # Per-agent guardrail filtering
    allowed_ids = None
    if agent_config and agent_config.get("guardrail_ids"):
        allowed_ids = set(agent_config["guardrail_ids"])

    for gr in guardrails:
        if not gr.get("enabled"):
            continue
        gid = gr["id"]
        name = gr["name"]
        # Per-agent filter: skip guardrails not in allowed list
        if allowed_ids is not None and gid not in allowed_ids:
            continue

        if gid == "gr-prompt-injection":
            lower = text.lower()
            cfg = gr.get("config", {})
            patterns = cfg.get("patterns", _INJECTION_PATTERNS)
            if not patterns:
                patterns = _INJECTION_PATTERNS
            for pat in patterns:
                if pat.lower() in lower:
                    results.append(
                        {
                            "guardrail": name,
                            "id": gid,
                            "status": "blocked",
                            "detail": f"Prompt injection pattern detected: '{pat}'",
                        }
                    )
                    break
            else:
                results.append(
                    {
                        "guardrail": name,
                        "id": gid,
                        "status": "passed",
                        "detail": "No injection detected",
                    }
                )

        elif gid == "gr-pii":
            found = []
            for ptype, regex in _PII_PATTERNS.items():
                if regex.search(text):
                    found.append(ptype)
            if found:
                results.append(
                    {
                        "guardrail": name,
                        "id": gid,
                        "status": "flagged",
                        "detail": f"PII detected: {', '.join(found)}",
                    }
                )
            else:
                results.append(
                    {
                        "guardrail": name,
                        "id": gid,
                        "status": "passed",
                        "detail": "No PII detected",
                    }
                )

        elif gid == "gr-topic-restrict":
            cfg = gr.get("config", {})
            blocked = cfg.get("blocked_topics", [])
            lower = text.lower()
            for topic in blocked:
                if topic.lower() in lower:
                    results.append(
                        {
                            "guardrail": name,
                            "id": gid,
                            "status": "blocked",
                            "detail": f"Blocked topic: '{topic}'",
                        }
                    )
                    break
            else:
                results.append(
                    {
                        "guardrail": name,
                        "id": gid,
                        "status": "passed",
                        "detail": "Topic allowed",
                    }
                )

    return results


def _check_guardrails_output(text: str, agent_config: dict | None = None) -> list[dict]:
    """Run enabled output guardrails. Returns list of {guardrail, status, detail}."""
    results = []
    try:
        from agent.memory import list_guardrails

        guardrails = list_guardrails()
    except Exception:
        return results

    allowed_ids = None
    if agent_config and agent_config.get("guardrail_ids"):
        allowed_ids = set(agent_config["guardrail_ids"])

    for gr in guardrails:
        if not gr.get("enabled"):
            continue
        gid = gr["id"]
        name = gr["name"]
        if allowed_ids is not None and gid not in allowed_ids:
            continue

        if gid == "gr-pii":
            found = []
            for ptype, regex in _PII_PATTERNS.items():
                if regex.search(text):
                    found.append(ptype)
            if found:
                results.append(
                    {
                        "guardrail": name,
                        "id": gid,
                        "status": "flagged",
                        "detail": f"PII in output: {', '.join(found)}",
                    }
                )
            else:
                results.append(
                    {
                        "guardrail": name,
                        "id": gid,
                        "status": "passed",
                        "detail": "Clean",
                    }
                )

        elif gid == "gr-output-length":
            cfg = gr.get("config", {})
            max_len = cfg.get("max_tokens", 2048)
            word_count = len(text.split())
            if word_count > max_len:
                results.append(
                    {
                        "guardrail": name,
                        "id": gid,
                        "status": "flagged",
                        "detail": f"Output {word_count} words exceeds limit {max_len}",
                    }
                )
            else:
                results.append(
                    {
                        "guardrail": name,
                        "id": gid,
                        "status": "passed",
                        "detail": f"{word_count} words (limit: {max_len})",
                    }
                )

        elif gid == "gr-data-leak":
            lower = text.lower()
            leak_patterns = [
                "system prompt:",
                "api_key",
                "internal configuration",
                "you are a helpful ai assistant with access to tools",
            ]
            for pat in leak_patterns:
                if pat in lower:
                    results.append(
                        {
                            "guardrail": name,
                            "id": gid,
                            "status": "flagged",
                            "detail": f"Potential data leak: system prompt fragment",
                        }
                    )
                    break
            else:
                results.append(
                    {
                        "guardrail": name,
                        "id": gid,
                        "status": "passed",
                        "detail": "No leakage detected",
                    }
                )

        elif gid == "gr-toxicity":
            toxic_words = ["kill", "hate", "destroy all"]
            lower = text.lower()
            for w in toxic_words:
                if w in lower:
                    results.append(
                        {
                            "guardrail": name,
                            "id": gid,
                            "status": "flagged",
                            "detail": f"Potentially toxic content detected",
                        }
                    )
                    break
            else:
                results.append(
                    {
                        "guardrail": name,
                        "id": gid,
                        "status": "passed",
                        "detail": "Content safe",
                    }
                )

    return results


# ── Prompt templates ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a helpful AI assistant with access to tools, a knowledge base, and conversation memory.

{memory_section}

{kb_section}

Available tools:
{tools}

When you need to use a tool, respond ONLY with a JSON block like:
{{"tool": "<tool_name>", "arguments": {{<key>: <value>, ...}}}}

If you do NOT need a tool, just answer the user directly in plain text.
Do NOT wrap your answer in JSON if you are not calling a tool.
Think step by step but be concise.
You can call tools multiple times in sequence to solve complex problems."""

FINAL_PROMPT = """\
The user asked: {prompt}

Tool results:
{tool_results}

Using the information above, provide a clear and helpful final answer to the user. Be concise."""


# ── State ───────────────────────────────────────────────────────────────────


class AgentState(TypedDict):
    prompt: str
    session_id: str
    request_id: str
    history: list[dict]
    kb_context: str
    memory_summary: str
    llm_raw: str
    tool_calls: list[dict]
    response: str
    tools_used: list[str]
    iteration: int


# ── Helpers ─────────────────────────────────────────────────────────────────

import re


def _parse_tool_calls(text: str) -> list[dict]:
    """
    Extract tool-call JSON from the LLM response.
    Supports both a single object and an array of objects.
    """
    json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```|(\{(?:[^{}]|\{[^{}]*\})*"tool"(?:[^{}]|\{[^{}]*\})*\})'
    matches = re.findall(json_pattern, text, re.DOTALL)

    calls: list[dict] = []
    for groups in matches:
        raw_json = groups[0] or groups[1]
        try:
            obj = json.loads(raw_json)
            if "tool" in obj:
                name = obj["tool"]
                args = obj.get("arguments", {})
                if any(t["name"] == name for t in TOOL_CATALOGUE):
                    calls.append({"name": name, "arguments": args, "result": None})
        except json.JSONDecodeError:
            continue

    if not calls:
        text_stripped = text.strip()
        if text_stripped.startswith("```"):
            text_stripped = re.sub(r"^```\w*\n?", "", text_stripped)
            text_stripped = re.sub(r"\n?```$", "", text_stripped)
        try:
            obj = json.loads(text_stripped)
            if isinstance(obj, dict) and "tool" in obj:
                name = obj["tool"]
                if any(t["name"] == name for t in TOOL_CATALOGUE):
                    calls.append(
                        {
                            "name": name,
                            "arguments": obj.get("arguments", {}),
                            "result": None,
                        }
                    )
        except (json.JSONDecodeError, ValueError):
            pass

    return calls


async def _ollama_chat(messages: list[dict], step: str = "default") -> str:
    """Call ChatOllama and return the content string."""
    llm = get_llm()
    lc_messages = []
    for m in messages:
        role = m["role"]
        content = m["content"]
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))

    with track_llm_call(step):
        result = await llm.ainvoke(lc_messages)
        return result.content


# ── Graph nodes ─────────────────────────────────────────────────────────────


async def retrieve_context(state: AgentState) -> dict:
    """Auto-retrieve relevant KB docs and build memory summary before reasoning."""
    import time as _time

    prompt = state["prompt"]
    session_id = state["session_id"]
    agent_config = state.get("agent_config")

    # ── Knowledge base retrieval ────────────────────────────────────────
    kb_context = ""
    use_kb = agent_config.get("use_kb", True) if agent_config else True
    kb_coll = agent_config.get("kb_collection") if agent_config else None
    skip_kb = (not use_kb) or len(prompt.strip()) < 20
    if skip_kb:
        logger.info(
            "req=%s kb_search SKIPPED (short query: %r)", state["request_id"], prompt
        )
    else:
        try:
            from agent.vectorstore import search_similar, get_collection_stats

            t0 = _time.time()
            stats = get_collection_stats(collection_name=kb_coll)
            total_chunks = stats.get("total_chunks", 0)
            logger.info(
                "req=%s kb_stats check took %dms  chunks=%d",
                state["request_id"],
                int((_time.time() - t0) * 1000),
                total_chunks,
            )
            if total_chunks > 0:
                t0 = _time.time()
                results = search_similar(prompt, k=3, collection_name=kb_coll)
                logger.info(
                    "req=%s kb_search took %dms  results=%d",
                    state["request_id"],
                    int((_time.time() - t0) * 1000),
                    len(results),
                )
                if results:
                    kb_snippets = []
                    for r in results:
                        if r.get("score", 1.0) < 0.8:  # cosine distance threshold
                            source = r.get("metadata", {}).get("source", "unknown")
                            kb_snippets.append(f"[{source}]: {r['content'][:500]}")
                    if kb_snippets:
                        kb_context = "\n---\n".join(kb_snippets)
        except Exception as e:
            logger.warning("KB retrieval failed: %s", e)

    # ── Memory summary ──────────────────────────────────────────────────
    memory_summary = ""
    try:
        summary = get_session_summary(session_id)
        if summary:
            memory_summary = summary
    except Exception as e:
        logger.warning("Memory summary failed: %s", e)

    logger.info(
        "req=%s kb_chunks=%d memory_summary=%s",
        state["request_id"],
        len(kb_context.split("---")) if kb_context else 0,
        "yes" if memory_summary else "no",
    )

    return {"kb_context": kb_context, "memory_summary": memory_summary}


async def reason(state: AgentState) -> dict:
    """Send the prompt + history + prior tool results to LLM; decide if more tools are needed."""
    import time as _time

    kb_context = state.get("kb_context", "")
    memory_summary = state.get("memory_summary", "")
    agent_config = state.get("agent_config")

    kb_section = ""
    if kb_context:
        kb_section = f"Relevant knowledge base context:\n{kb_context}"
    else:
        kb_section = "No relevant knowledge base documents found for this query."

    memory_section = ""
    if memory_summary:
        memory_section = f"Conversation summary so far:\n{memory_summary}"
    else:
        memory_section = "This is a new conversation with no prior context."

    system = SYSTEM_PROMPT.format(
        tools=catalogue_as_text(),
        kb_section=kb_section,
        memory_section=memory_section,
    )

    # Merge agent custom prompt + skill prompts
    extra_system_parts = []
    if agent_config:
        if agent_config.get("system_prompt"):
            extra_system_parts.append(agent_config["system_prompt"])
        skill_ids = agent_config.get("skill_ids", [])
        if skill_ids:
            from agent.memory import get_skill

            for sid in skill_ids:
                sk = get_skill(sid)
                if sk and sk.get("system_prompt"):
                    extra_system_parts.append(
                        f"[Skill: {sk['name']}]\n{sk['system_prompt']}"
                    )
        # Inject sub-agent list for orchestrators
        sub_agent_ids = agent_config.get("sub_agent_ids", [])
        if sub_agent_ids:
            from agent.memory import get_agent

            sub_agents_desc = []
            for sa_id in sub_agent_ids:
                sa = get_agent(sa_id)
                if sa:
                    sub_agents_desc.append(
                        f"- {sa['name']} (id: {sa['id']}): {sa.get('description', '')}"
                    )
            if sub_agents_desc:
                extra_system_parts.append(
                    "[Orchestration]\n"
                    "You can delegate tasks to these sub-agents using the delegate_to_agent tool:\n"
                    + "\n".join(sub_agents_desc)
                    + "\n"
                    "Use delegate_to_agent when a sub-agent is better suited for a specific part of the task."
                )
    if extra_system_parts:
        system += "\n\n" + "\n\n".join(extra_system_parts)

    iteration = state.get("iteration", 0)

    messages = [{"role": "system", "content": system}]
    for msg in state.get("history", []):
        messages.append(msg)
    messages.append({"role": "user", "content": state["prompt"]})

    # Append prior tool results if this is a subsequent iteration
    existing_calls = state.get("tool_calls", [])
    if existing_calls:
        results_text = "\n".join(
            f"Tool '{tc['name']}' returned: {json.dumps(tc.get('result', {}))}"
            for tc in existing_calls
            if tc.get("result") is not None
        )
        messages.append(
            {
                "role": "assistant",
                "content": f"I called some tools. Results:\n{results_text}\n\nLet me decide if I need more tools or can answer now.",
            }
        )

    t0 = _time.time()
    raw = await _ollama_chat(messages, step=f"reason_iter_{iteration}")
    logger.info(
        "req=%s reason iter=%d took %dms raw=%s",
        state["request_id"],
        iteration,
        int((_time.time() - t0) * 1000),
        raw[:200],
    )

    new_tool_calls = _parse_tool_calls(raw)

    return {
        "llm_raw": raw,
        "tool_calls": existing_calls + new_tool_calls,
        "tools_used": state.get("tools_used", [])
        + [tc["name"] for tc in new_tool_calls],
        "iteration": iteration + 1,
    }


async def execute_tools(state: AgentState) -> dict:
    """Execute only the tool calls that don't have results yet."""
    tool_calls = state.get("tool_calls", [])
    for tc in tool_calls:
        if tc.get("result") is not None:
            continue  # Already executed
        tool_call_counter.labels(tool_name=tc["name"]).inc()
        result = await call_tool(tc["name"], tc["arguments"])
        tc["result"] = result
        logger.info(
            "req=%s tool=%s result=%s",
            state["request_id"],
            tc["name"],
            str(result)[:200],
        )
    return {"tool_calls": tool_calls}


async def generate_response(state: AgentState) -> dict:
    """Produce the final answer, synthesizing tool results if any."""
    tool_calls = state.get("tool_calls", [])

    if not tool_calls:
        response = state.get("llm_raw", "I'm sorry, I couldn't process that.")
    else:
        results_text = "\n".join(
            f"- {tc['name']}({tc['arguments']}): {json.dumps(tc.get('result', {}))}"
            for tc in tool_calls
        )
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Synthesise tool results into a clear answer.",
            },
            {
                "role": "user",
                "content": FINAL_PROMPT.format(
                    prompt=state["prompt"],
                    tool_results=results_text,
                ),
            },
        ]
        response = await _ollama_chat(messages, step="generate_response")

    save_message(state["session_id"], "user", state["prompt"])
    save_message(state["session_id"], "assistant", response)

    # Update conversation summary for long-term memory
    try:
        update_session_summary(state["session_id"], state["prompt"], response)
    except Exception as e:
        logger.warning("Failed to update session summary: %s", e)

    return {"response": response}


# ── Routing ─────────────────────────────────────────────────────────────────


def should_continue(state: AgentState) -> str:
    """Decide: execute tools, continue reasoning, or finalize."""
    tool_calls = state.get("tool_calls", [])
    iteration = state.get("iteration", 0)

    # Check if the latest reasoning produced new unexecuted tool calls
    has_pending = any(tc.get("result") is None for tc in tool_calls)

    if has_pending:
        return "execute_tools"

    if iteration >= MAX_ITERATIONS:
        return "generate_response"

    return "generate_response"


def after_tools(state: AgentState) -> str:
    """After tool execution, decide to reason again or finalize."""
    iteration = state.get("iteration", 0)
    if iteration < MAX_ITERATIONS:
        # Could reason again, but for now go to response
        # The reason node re-evaluates if more tools needed
        return "generate_response"
    return "generate_response"


# ── Build graph ─────────────────────────────────────────────────────────────


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("retrieve_context", retrieve_context)
    g.add_node("reason", reason)
    g.add_node("execute_tools", execute_tools)
    g.add_node("generate_response", generate_response)

    g.set_entry_point("retrieve_context")
    g.add_edge("retrieve_context", "reason")
    g.add_conditional_edges(
        "reason",
        should_continue,
        {
            "execute_tools": "execute_tools",
            "generate_response": "generate_response",
        },
    )
    g.add_edge("execute_tools", "generate_response")
    g.add_edge("generate_response", END)

    return g.compile()


_graph = build_graph()


# ── Public API ──────────────────────────────────────────────────────────────


async def run_agent(
    prompt: str, session_id: str, request_id: str, agent_config: dict | None = None
) -> dict:
    """Run the agent graph and return {response, tools_used, trace_id}."""
    lf_trace = LangfuseTrace("agent-run", session_id, request_id, prompt)

    memory_window = 5
    if agent_config:
        memory_window = agent_config.get("memory_window", 5) or 5

    history = get_history(session_id, limit=memory_window)
    initial_state: AgentState = {
        "prompt": prompt,
        "session_id": session_id,
        "request_id": request_id,
        "history": history,
        "kb_context": "",
        "memory_summary": "",
        "llm_raw": "",
        "tool_calls": [],
        "response": "",
        "tools_used": [],
        "iteration": 0,
        "agent_config": agent_config,
    }

    try:
        result = await _graph.ainvoke(initial_state)
        agent_run_counter.labels(status="success").inc()
        lf_trace.end(output=result.get("response", ""))
    except Exception as e:
        agent_run_counter.labels(status="error").inc()
        lf_trace.end(output=f"ERROR: {e}")
        raise

    return {
        "response": result.get("response", "No response generated."),
        "tools_used": result.get("tools_used", []),
        "trace_id": lf_trace.trace_id,
    }


# ── Streaming support ──────────────────────────────────────────────────────


async def _ollama_chat_stream(
    messages: list[dict], usage_out: dict | None = None
) -> AsyncIterator[str]:
    """Stream tokens from ChatOllama.  If *usage_out* is supplied, the final
    chunk's ``usage_metadata`` is written into it (keys: prompt_tokens,
    completion_tokens, total_tokens)."""
    llm = get_llm()
    lc_messages = []
    for m in messages:
        role = m["role"]
        content = m["content"]
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))

    async for chunk in llm.astream(lc_messages):
        if chunk.content:
            yield chunk.content
        # Capture token usage from the last chunk (OpenAI/Azure attach it there)
        if usage_out is not None:
            um = getattr(chunk, "usage_metadata", None)
            if um:
                usage_out["prompt_tokens"] = getattr(um, "input_tokens", 0) or um.get(
                    "input_tokens", 0
                )
                usage_out["completion_tokens"] = getattr(
                    um, "output_tokens", 0
                ) or um.get("output_tokens", 0)
                usage_out["total_tokens"] = getattr(um, "total_tokens", 0) or um.get(
                    "total_tokens", 0
                )


async def run_agent_stream(
    prompt: str,
    session_id: str,
    request_id: str,
    agent_config: dict | None = None,
) -> AsyncIterator[dict]:
    """
    Run the agent graph with streaming.
    Yields SSE-compatible dicts with structured step events.
    agent_config: optional dict with provider, model, system_prompt, skill_ids, tool_ids, kb_collection, etc.
    """
    import time as _time

    lf_trace = LangfuseTrace("agent-run-stream", session_id, request_id, prompt)

    # Configurable memory window from agent config
    memory_window = 5
    max_iterations = MAX_ITERATIONS
    if agent_config:
        memory_window = agent_config.get("memory_window", 5) or 5
        max_iterations = (
            agent_config.get("max_iterations", MAX_ITERATIONS) or MAX_ITERATIONS
        )
    history = get_history(session_id, limit=memory_window)

    # Build merged system prompt from agent config + skills
    extra_system_parts = []
    if agent_config:
        if agent_config.get("system_prompt"):
            extra_system_parts.append(agent_config["system_prompt"])
        # Resolve skills into additional system prompts
        skill_ids = agent_config.get("skill_ids", [])
        if skill_ids:
            from agent.memory import get_skill

            for sid in skill_ids:
                sk = get_skill(sid)
                if sk and sk.get("system_prompt"):
                    extra_system_parts.append(
                        f"[Skill: {sk['name']}]\n{sk['system_prompt']}"
                    )

    agent_extra_prompt = "\n\n".join(extra_system_parts) if extra_system_parts else ""

    # ── Step 0: Input guardrails ────────────────────────────────────────
    yield {
        "event": "step",
        "data": {
            "step": "guardrails_input",
            "status": "started",
            "label": "Running input guardrails",
        },
    }
    t0 = _time.time()
    input_gr_results = _check_guardrails_input(prompt, agent_config=agent_config)
    blocked = [g for g in input_gr_results if g["status"] == "blocked"]
    yield {
        "event": "guardrails",
        "data": {"phase": "input", "results": input_gr_results},
    }
    yield {
        "event": "step",
        "data": {
            "step": "guardrails_input",
            "status": "done",
            "duration_ms": int((_time.time() - t0) * 1000),
            "detail": f"{len(input_gr_results)} checks, {len(blocked)} blocked",
        },
    }

    if blocked:
        block_msg = "Request blocked by guardrails: " + "; ".join(
            [g["detail"] for g in blocked]
        )
        yield {"event": "token", "data": block_msg}
        yield {
            "event": "done",
            "data": {
                "response": block_msg,
                "tools_used": [],
                "request_id": request_id,
                "trace_id": "",
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
                "model": "",
                "provider": "",
                "guardrails": {"input": input_gr_results, "output": []},
            },
        }
        return

    # ── Step 1: Retrieve context ────────────────────────────────────────
    use_kb = agent_config.get("use_kb", True) if agent_config else True
    yield {
        "event": "step",
        "data": {
            "step": "retrieve_context",
            "status": "started",
            "label": (
                "Retrieving from Knowledge Base"
                if use_kb
                else "KB retrieval skipped (disabled)"
            ),
        },
    }
    t0 = _time.time()

    kb_context = ""
    kb_chunks = 0
    kb_coll = agent_config.get("kb_collection") if agent_config else None
    # Skip KB entirely if user toggled it off, or for very short queries
    skip_kb = (not use_kb) or len(prompt.strip()) < 20
    if skip_kb:
        logger.info(
            "req=%s stream kb_search SKIPPED (use_kb=%s, short=%s)",
            request_id,
            use_kb,
            len(prompt.strip()) < 20,
        )
    else:
        try:
            from agent.vectorstore import search_similar, get_collection_stats

            stats = get_collection_stats(collection_name=kb_coll)
            total_chunks = stats.get("total_chunks", 0)
            logger.info("req=%s stream kb_stats chunks=%d", request_id, total_chunks)
            if total_chunks > 0:
                results = search_similar(prompt, k=3, collection_name=kb_coll)
                snippets = [
                    f"[{r.get('metadata',{}).get('source','unknown')}]: {r['content'][:500]}"
                    for r in results
                    if r.get("score", 1.0) < 0.8
                ]
                if snippets:
                    kb_context = "\n---\n".join(snippets)
                    kb_chunks = len(snippets)
        except Exception:
            logger.warning(
                "req=%s stream KB retrieval skipped (unavailable)", request_id
            )

    yield {
        "event": "step",
        "data": {
            "step": "retrieve_context",
            "status": "done",
            "duration_ms": int((_time.time() - t0) * 1000),
            "detail": "Disabled" if not use_kb else f"Found {kb_chunks} chunks",
        },
    }

    # ── Step 2: Load memory ─────────────────────────────────────────────
    yield {
        "event": "step",
        "data": {
            "step": "load_memory",
            "status": "started",
            "label": "Loading conversation memory",
        },
    }
    t0 = _time.time()

    memory_summary = get_session_summary(session_id) or ""

    yield {
        "event": "step",
        "data": {
            "step": "load_memory",
            "status": "done",
            "duration_ms": int((_time.time() - t0) * 1000),
            "detail": "Has context" if memory_summary else "New conversation",
        },
    }

    # ── Step 3: Reasoning ───────────────────────────────────────────────
    kb_section = (
        f"Relevant knowledge base context:\n{kb_context}"
        if kb_context
        else "No relevant knowledge base documents found for this query."
    )
    memory_section = (
        f"Conversation summary so far:\n{memory_summary}"
        if memory_summary
        else "This is a new conversation with no prior context."
    )

    yield {
        "event": "step",
        "data": {
            "step": "reason",
            "status": "started",
            "label": "Reasoning",
            "iteration": 1,
        },
    }
    t0 = _time.time()

    system = SYSTEM_PROMPT.format(
        tools=catalogue_as_text(), kb_section=kb_section, memory_section=memory_section
    )
    if agent_extra_prompt:
        system += "\n\n" + agent_extra_prompt
    messages = [{"role": "system", "content": system}]
    for msg in history:
        messages.append(msg)
    messages.append({"role": "user", "content": prompt})

    # Langfuse generation for reasoning LLM call
    active_info = _get_active_model()
    lf_gen_reason = lf_trace.generation(
        name="reasoning",
        model=(
            agent_config.get("model", active_info["model"])
            if agent_config
            else active_info["model"]
        ),
        input=messages,
    )

    # Stream reasoning tokens — if no tool call is detected, these become
    # the final response and the user sees tokens arriving immediately
    # instead of waiting for the full LLM response before streaming starts.
    raw = ""
    usage_reason: dict = {}
    async for token in _ollama_chat_stream(messages, usage_out=usage_reason):
        raw += token
    logger.info("req=%s reason raw=%s", request_id, raw[:200])
    tool_calls = _parse_tool_calls(raw)
    tools_used = [tc["name"] for tc in tool_calls]

    reason_ms = int((_time.time() - t0) * 1000)
    lf_gen_reason.end(
        output=raw[:500],
        usage={
            "input": usage_reason.get("prompt_tokens", 0),
            "output": usage_reason.get("completion_tokens", 0),
            "total": usage_reason.get("total_tokens", 0),
        },
    )

    yield {
        "event": "step",
        "data": {
            "step": "reason",
            "status": "done",
            "duration_ms": reason_ms,
            "detail": f"{'Needs tools: ' + ', '.join(tools_used) if tools_used else 'Direct answer'}",
        },
    }

    # ── Step 4: Tool execution (if needed) ──────────────────────────────
    if tool_calls:
        for tc in tool_calls:
            yield {
                "event": "step",
                "data": {
                    "step": "tool_call",
                    "status": "started",
                    "label": f"Calling tool: {tc['name']}",
                    "tool": tc["name"],
                    "args": tc["arguments"],
                },
            }
            t0 = _time.time()
            tool_call_counter.labels(tool_name=tc["name"]).inc()
            lf_tool_span = lf_trace.span(
                name=f"tool:{tc['name']}", input=tc["arguments"]
            )
            result = await call_tool(tc["name"], tc["arguments"])
            tc["result"] = result
            logger.info(
                "req=%s tool=%s result=%s", request_id, tc["name"], str(result)[:200]
            )
            lf_tool_span.end(output=str(result)[:500])
            yield {
                "event": "step",
                "data": {
                    "step": "tool_call",
                    "status": "done",
                    "duration_ms": int((_time.time() - t0) * 1000),
                    "tool": tc["name"],
                    "detail": str(result)[:150],
                },
            }

    # ── Step 5: Generating response ─────────────────────────────────────
    yield {
        "event": "step",
        "data": {
            "step": "generate_response",
            "status": "started",
            "label": "Generating response",
        },
    }
    t0 = _time.time()

    full_response = ""
    usage_synth: dict = {}
    if not tool_calls:
        full_response = raw
        for word in raw.split(" "):
            yield {"event": "token", "data": word + " "}
    else:
        results_text = "\n".join(
            f"- {tc['name']}({tc['arguments']}): {json.dumps(tc.get('result', {}))}"
            for tc in tool_calls
        )
        synth_messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Synthesise tool results into a clear answer.",
            },
            {
                "role": "user",
                "content": FINAL_PROMPT.format(
                    prompt=prompt, tool_results=results_text
                ),
            },
        ]
        lf_gen_synth = lf_trace.generation(
            name="synthesis",
            model=(
                agent_config.get("model", active_info["model"])
                if agent_config
                else active_info["model"]
            ),
            input=synth_messages,
        )
        async for token in _ollama_chat_stream(synth_messages, usage_out=usage_synth):
            full_response += token
            yield {"event": "token", "data": token}
        lf_gen_synth.end(
            output=full_response[:500],
            usage={
                "input": usage_synth.get("prompt_tokens", 0),
                "output": usage_synth.get("completion_tokens", 0),
                "total": usage_synth.get("total_tokens", 0),
            },
        )

    # Aggregate token usage across LLM calls
    total_usage = {
        "prompt_tokens": usage_reason.get("prompt_tokens", 0)
        + usage_synth.get("prompt_tokens", 0),
        "completion_tokens": usage_reason.get("completion_tokens", 0)
        + usage_synth.get("completion_tokens", 0),
        "total_tokens": usage_reason.get("total_tokens", 0)
        + usage_synth.get("total_tokens", 0),
    }

    yield {
        "event": "step",
        "data": {
            "step": "generate_response",
            "status": "done",
            "duration_ms": int((_time.time() - t0) * 1000),
            "detail": f"{len(full_response)} chars",
        },
    }

    save_message(session_id, "user", prompt)
    save_message(session_id, "assistant", full_response)
    try:
        update_session_summary(session_id, prompt, full_response)
    except Exception:
        pass

    agent_run_counter.labels(status="success").inc()

    # ── Output guardrails ───────────────────────────────────────────────
    yield {
        "event": "step",
        "data": {
            "step": "guardrails_output",
            "status": "started",
            "label": "Running output guardrails",
        },
    }
    t0 = _time.time()
    output_gr_results = _check_guardrails_output(
        full_response, agent_config=agent_config
    )
    yield {
        "event": "guardrails",
        "data": {"phase": "output", "results": output_gr_results},
    }
    yield {
        "event": "step",
        "data": {
            "step": "guardrails_output",
            "status": "done",
            "duration_ms": int((_time.time() - t0) * 1000),
            "detail": f"{len(output_gr_results)} checks",
        },
    }

    lf_trace.update(
        output=full_response,
        metadata={
            "request_id": request_id,
            "tools_used": tools_used,
            "model": (
                agent_config.get("model")
                if agent_config and agent_config.get("model")
                else active_info["model"]
            ),
            "provider": (
                agent_config.get("provider")
                if agent_config and agent_config.get("provider")
                else active_info["provider"]
            ),
            "usage": total_usage,
        },
    )
    lf_trace.end(output=full_response)
    logger.info("req=%s done tools=%s tokens=%s", request_id, tools_used, total_usage)
    yield {
        "event": "done",
        "data": {
            "response": full_response,
            "tools_used": tools_used,
            "request_id": request_id,
            "trace_id": lf_trace.trace_id,
            "usage": total_usage,
            "model": (
                agent_config.get("model")
                if agent_config and agent_config.get("model")
                else _get_active_model()["model"]
            ),
            "provider": (
                agent_config.get("provider")
                if agent_config and agent_config.get("provider")
                else _get_active_model()["provider"]
            ),
            "guardrails": {"input": input_gr_results, "output": output_gr_results},
        },
    }
