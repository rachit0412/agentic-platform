"""
Structured Data Querying — natural language → SQL/Pandas.

Uses LlamaIndex's NLSQLTableQueryEngine and PandasQueryEngine
to let agents query databases and DataFrames using natural language.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger("agent-service.structured-query")


def query_sql(
    question: str,
    connection_string: str,
    tables: Optional[list[str]] = None,
) -> dict:
    """Natural language → SQL query execution.

    Args:
        question: Natural language question (e.g. "How many users signed up last month?")
        connection_string: SQLAlchemy connection string
        tables: Optional list of table names to include (all if omitted)

    Returns:
        dict with sql_query, result, and natural_language_response
    """
    from llama_index.core import SQLDatabase
    from llama_index.core.query_engine import NLSQLTableQueryEngine
    from llama_index.llms.langchain import LangChainLLM
    from llama_index.embeddings.langchain import LangchainEmbedding
    from llama_index.core import Settings
    from agent.llm import get_llm, get_embeddings
    from sqlalchemy import create_engine

    Settings.llm = LangChainLLM(llm=get_llm())
    Settings.embed_model = LangchainEmbedding(get_embeddings())

    engine = create_engine(connection_string)
    sql_database = SQLDatabase(engine, include_tables=tables)

    query_engine = NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=tables,
    )

    try:
        response = query_engine.query(question)
        result = {
            "question": question,
            "sql_query": getattr(response, "metadata", {}).get("sql_query", ""),
            "result": str(response),
            "source_tables": tables or "all",
        }
        logger.info("SQL query: %s → %s", question[:60], result["sql_query"][:100])
        return result
    except Exception as e:
        logger.error("SQL query failed: %s — %s", question[:60], e)
        return {"question": question, "error": str(e)}


def query_csv(
    question: str,
    csv_path: str,
) -> dict:
    """Natural language query over a CSV file using Pandas.

    Args:
        question: Natural language question about the data
        csv_path: Path to CSV file

    Returns:
        dict with result and any generated code
    """
    from llama_index.core.query_engine import PandasQueryEngine
    from llama_index.llms.langchain import LangChainLLM
    from llama_index.core import Settings
    from agent.llm import get_llm
    import pandas as pd

    Settings.llm = LangChainLLM(llm=get_llm())

    df = pd.read_csv(csv_path)
    query_engine = PandasQueryEngine(df=df, verbose=True)

    try:
        response = query_engine.query(question)
        result = {
            "question": question,
            "result": str(response),
            "row_count": len(df),
            "columns": list(df.columns),
        }
        logger.info("CSV query: %s → %s", question[:60], str(response)[:100])
        return result
    except Exception as e:
        logger.error("CSV query failed: %s — %s", question[:60], e)
        return {"question": question, "error": str(e)}


def query_dataframe(
    question: str,
    data: list[dict],
) -> dict:
    """Natural language query over in-memory data (list of dicts).

    Args:
        question: Natural language question
        data: List of row dicts (e.g. from an API response)

    Returns:
        dict with result
    """
    from llama_index.core.query_engine import PandasQueryEngine
    from llama_index.llms.langchain import LangChainLLM
    from llama_index.core import Settings
    from agent.llm import get_llm
    import pandas as pd

    Settings.llm = LangChainLLM(llm=get_llm())

    df = pd.DataFrame(data)
    query_engine = PandasQueryEngine(df=df, verbose=True)

    try:
        response = query_engine.query(question)
        return {
            "question": question,
            "result": str(response),
            "row_count": len(df),
            "columns": list(df.columns),
        }
    except Exception as e:
        logger.error("DataFrame query failed: %s — %s", question[:60], e)
        return {"question": question, "error": str(e)}


def get_table_schema(
    connection_string: str,
    tables: Optional[list[str]] = None,
) -> dict:
    """Inspect database schema — returns table names, columns, and types."""
    from sqlalchemy import create_engine, inspect

    engine = create_engine(connection_string)
    inspector = inspect(engine)

    all_tables = inspector.get_table_names()
    target_tables = tables or all_tables

    schema = {}
    for table in target_tables:
        if table not in all_tables:
            continue
        columns = []
        for col in inspector.get_columns(table):
            columns.append(
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                }
            )
        schema[table] = {
            "columns": columns,
            "row_count": None,  # Avoid expensive COUNT(*) by default
        }

    return {"tables": schema, "total_tables": len(schema)}
