"""
RAG Evaluation — quality scoring for retrieval and generation.

Evaluates RAG pipelines on:
  1. Faithfulness  — Is the response grounded in the retrieved context?
  2. Relevancy     — Are the retrieved documents relevant to the query?
  3. Correctness   — Does the response correctly answer the question?
  4. Guideline     — Does the response follow specified guidelines?

Uses LlamaIndex's built-in evaluation modules with the active LLM.
"""

import logging
from typing import Optional

logger = logging.getLogger("agent-service.rag-evaluation")


def _setup_settings():
    """Configure LlamaIndex Settings with the active LLM/embeddings."""
    from llama_index.core import Settings
    from llama_index.llms.langchain import LangChainLLM
    from llama_index.embeddings.langchain import LangchainEmbedding
    from agent.llm import get_llm, get_embeddings

    Settings.llm = LangChainLLM(llm=get_llm())
    Settings.embed_model = LangchainEmbedding(get_embeddings())


def evaluate_faithfulness(
    query: str,
    response: str,
    contexts: list[str],
) -> dict:
    """Evaluate whether the response is faithful to the retrieved context.

    Returns score 0.0-1.0 and per-statement verdicts.
    """
    from llama_index.core.evaluation import FaithfulnessEvaluator

    _setup_settings()
    evaluator = FaithfulnessEvaluator()

    try:
        context_str = "\n\n---\n\n".join(contexts)
        result = evaluator.evaluate(
            query=query,
            response=response,
            contexts=[context_str],
        )
        return {
            "metric": "faithfulness",
            "score": float(result.score) if result.score is not None else 0.0,
            "passing": result.passing,
            "feedback": result.feedback or "",
        }
    except Exception as e:
        logger.error("Faithfulness evaluation failed: %s", e)
        return {"metric": "faithfulness", "score": 0.0, "error": str(e)}


def evaluate_relevancy(
    query: str,
    response: str,
    contexts: list[str],
) -> dict:
    """Evaluate whether retrieved contexts are relevant to the query."""
    from llama_index.core.evaluation import RelevancyEvaluator

    _setup_settings()
    evaluator = RelevancyEvaluator()

    try:
        context_str = "\n\n---\n\n".join(contexts)
        result = evaluator.evaluate(
            query=query,
            response=response,
            contexts=[context_str],
        )
        return {
            "metric": "relevancy",
            "score": float(result.score) if result.score is not None else 0.0,
            "passing": result.passing,
            "feedback": result.feedback or "",
        }
    except Exception as e:
        logger.error("Relevancy evaluation failed: %s", e)
        return {"metric": "relevancy", "score": 0.0, "error": str(e)}


def evaluate_correctness(
    query: str,
    response: str,
    reference: Optional[str] = None,
) -> dict:
    """Evaluate response correctness (optionally against a reference answer)."""
    from llama_index.core.evaluation import CorrectnessEvaluator

    _setup_settings()
    evaluator = CorrectnessEvaluator()

    try:
        result = evaluator.evaluate(
            query=query,
            response=response,
            reference=reference,
        )
        return {
            "metric": "correctness",
            "score": float(result.score) if result.score is not None else 0.0,
            "passing": result.passing,
            "feedback": result.feedback or "",
        }
    except Exception as e:
        logger.error("Correctness evaluation failed: %s", e)
        return {"metric": "correctness", "score": 0.0, "error": str(e)}


def evaluate_guideline_adherence(
    query: str,
    response: str,
    guidelines: list[str],
) -> dict:
    """Evaluate whether the response follows specified guidelines."""
    from llama_index.core.evaluation import GuidelineEvaluator

    _setup_settings()

    results = []
    overall_score = 0.0

    for guideline in guidelines:
        try:
            evaluator = GuidelineEvaluator(guidelines=guideline)
            result = evaluator.evaluate(
                query=query,
                response=response,
            )
            score = float(result.score) if result.score is not None else 0.0
            results.append(
                {
                    "guideline": guideline,
                    "score": score,
                    "passing": result.passing,
                    "feedback": result.feedback or "",
                }
            )
            overall_score += score
        except Exception as e:
            results.append(
                {
                    "guideline": guideline,
                    "score": 0.0,
                    "error": str(e),
                }
            )

    avg_score = overall_score / max(len(guidelines), 1)
    return {
        "metric": "guideline_adherence",
        "score": avg_score,
        "guidelines_evaluated": len(results),
        "details": results,
    }


def evaluate_rag_pipeline(
    query: str,
    response: str,
    contexts: list[str],
    reference: Optional[str] = None,
    guidelines: Optional[list[str]] = None,
) -> dict:
    """Run all applicable evaluations on a RAG response.

    Returns a combined report with all metrics.
    """
    report = {
        "query": query,
        "response_length": len(response),
        "context_count": len(contexts),
        "metrics": {},
    }

    # Always evaluate faithfulness and relevancy (need contexts)
    if contexts:
        report["metrics"]["faithfulness"] = evaluate_faithfulness(
            query, response, contexts
        )
        report["metrics"]["relevancy"] = evaluate_relevancy(query, response, contexts)

    # Correctness (optionally with reference)
    report["metrics"]["correctness"] = evaluate_correctness(query, response, reference)

    # Guideline adherence (if guidelines provided)
    if guidelines:
        report["metrics"]["guideline_adherence"] = evaluate_guideline_adherence(
            query, response, guidelines
        )

    # Compute overall score
    scores = [
        m.get("score", 0)
        for m in report["metrics"].values()
        if isinstance(m.get("score"), (int, float))
    ]
    report["overall_score"] = sum(scores) / max(len(scores), 1)
    report["passing"] = all(
        m.get("passing", False) for m in report["metrics"].values() if "passing" in m
    )

    logger.info(
        "RAG evaluation: query=%s overall=%.2f passing=%s",
        query[:50],
        report["overall_score"],
        report["passing"],
    )
    return report


def batch_evaluate(
    test_cases: list[dict],
) -> dict:
    """Evaluate multiple query-response pairs.

    Each test_case should have: query, response, contexts, and optionally reference/guidelines.

    Returns aggregate metrics.
    """
    results = []
    for i, tc in enumerate(test_cases):
        result = evaluate_rag_pipeline(
            query=tc["query"],
            response=tc["response"],
            contexts=tc.get("contexts", []),
            reference=tc.get("reference"),
            guidelines=tc.get("guidelines"),
        )
        result["test_case_index"] = i
        results.append(result)

    # Aggregate
    if results:
        avg_overall = sum(r["overall_score"] for r in results) / len(results)
        passing_count = sum(1 for r in results if r.get("passing", False))
    else:
        avg_overall = 0.0
        passing_count = 0

    return {
        "total_cases": len(results),
        "passing_count": passing_count,
        "failing_count": len(results) - passing_count,
        "average_score": avg_overall,
        "results": results,
    }
