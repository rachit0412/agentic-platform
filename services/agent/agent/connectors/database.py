"""
Database Connector — Pull data from PostgreSQL, MySQL, SQL Server.

Executes a user-defined query and converts rows into documents
staged in the filestore for indexing.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def pull_database(config: dict) -> list[dict]:
    """
    Connect to database, execute query, return list of documents.
    Each document: {"name": str, "content": str, "metadata": dict}
    """
    db_type = config["db_type"]
    host = config["host"]
    port = int(config["port"])
    database = config["database"]
    username = config["username"]
    password = config["password"]
    query = config["query"]
    text_columns = [c.strip() for c in config["text_columns"].split(",")]

    rows = _execute_query(db_type, host, port, database, username, password, query)

    documents = []
    for i, row in enumerate(rows):
        content_parts = []
        for col in text_columns:
            if col in row and row[col]:
                content_parts.append(str(row[col]))
        content = "\n\n".join(content_parts)
        if not content.strip():
            continue

        name = row.get("title") or row.get("name") or row.get("id") or f"row_{i+1}"
        documents.append({
            "name": str(name),
            "content": content,
            "metadata": {k: str(v) for k, v in row.items() if k not in text_columns},
        })

    logger.info(f"Database connector pulled {len(documents)} documents from {db_type}://{host}/{database}")
    return documents


def test_connection(config: dict) -> dict:
    """Test database connectivity. Returns {"ok": bool, "message": str}."""
    try:
        db_type = config["db_type"]
        host = config["host"]
        port = int(config["port"])
        database = config["database"]
        username = config["username"]
        password = config["password"]

        conn = _get_connection(db_type, host, port, database, username, password)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"ok": True, "message": f"Connected to {db_type}://{host}:{port}/{database}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


def _get_connection(db_type: str, host: str, port: int, database: str, username: str, password: str):
    """Get a database connection based on type."""
    if db_type == "postgresql":
        try:
            import psycopg2
        except ImportError:
            raise ImportError("psycopg2 not installed. Run: pip install psycopg2-binary")
        return psycopg2.connect(host=host, port=port, dbname=database, user=username, password=password)
    elif db_type == "mysql":
        try:
            import pymysql
        except ImportError:
            raise ImportError("pymysql not installed. Run: pip install pymysql")
        return pymysql.connect(host=host, port=port, database=database, user=username, password=password)
    elif db_type == "mssql":
        try:
            import pymssql
        except ImportError:
            raise ImportError("pymssql not installed. Run: pip install pymssql")
        return pymssql.connect(server=host, port=port, database=database, user=username, password=password)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def _execute_query(db_type: str, host: str, port: int, database: str, username: str, password: str, query: str) -> list[dict]:
    """Execute query and return rows as list of dicts."""
    conn = _get_connection(db_type, host, port, database, username, password)
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        rows = []
        for row in cursor.fetchall():
            rows.append(dict(zip(columns, row)))
        cursor.close()
        return rows
    finally:
        conn.close()
