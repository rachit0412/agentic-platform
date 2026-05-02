"""
Sync Engine — Orchestrates connector pulls into the filestore pipeline.

Manages connector configs (stored in SQLite) and sync job history.
Pipeline: Connector → Pull docs → Stage in filestore → (optional) auto-index to ChromaDB
"""

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from . import ConnectorType, SyncStatus, CONNECTOR_CATALOG, generate_connector_id, generate_job_id, now_iso
from .database import pull_database, test_connection as test_db
from .cloud_storage import pull_cloud_storage, test_connection as test_cloud
from .api_connector import pull_api, test_connection as test_api
from .drives import pull_google_drive, test_google_drive, pull_sharepoint, test_sharepoint

logger = logging.getLogger(__name__)


def test_connector(connector_type: str, config: dict) -> dict:
    """Test a connector's connectivity without saving anything."""
    if connector_type == "database":
        return test_db(config)
    elif connector_type == "cloud_storage":
        return test_cloud(config)
    elif connector_type == "api":
        return test_api(config)
    elif connector_type == "google_drive":
        return test_google_drive(config)
    elif connector_type == "sharepoint":
        return test_sharepoint(config)
    elif connector_type == "airbyte":
        return _test_airbyte(config)
    else:
        return {"ok": False, "message": f"Unknown connector type: {connector_type}"}


def run_sync(connector_type: str, config: dict) -> list[dict]:
    """
    Execute a sync: pull documents from the source.
    Returns list of {"name": str, "content": str, "metadata": dict}
    """
    if connector_type == "database":
        return pull_database(config)
    elif connector_type == "cloud_storage":
        return pull_cloud_storage(config)
    elif connector_type == "api":
        return pull_api(config)
    elif connector_type == "google_drive":
        return pull_google_drive(config)
    elif connector_type == "sharepoint":
        return pull_sharepoint(config)
    elif connector_type == "airbyte":
        return _run_airbyte_sync(config)
    else:
        raise ValueError(f"Unknown connector type: {connector_type}")


def _test_airbyte(config: dict) -> dict:
    """Test Airbyte sidecar connectivity."""
    try:
        import httpx
        url = config.get("airbyte_url", "http://airbyte:8000")
        r = httpx.get(f"{url}/api/v1/health", timeout=5)
        if r.status_code == 200:
            return {"ok": True, "message": "Airbyte is healthy"}
        return {"ok": False, "message": f"Airbyte returned HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "message": f"Cannot reach Airbyte: {e}"}


def _run_airbyte_sync(config: dict) -> list[dict]:
    """Trigger an Airbyte sync and wait for results."""
    import httpx
    url = config.get("airbyte_url", "http://airbyte:8000")
    connection_id = config["connection_id"]

    # Trigger sync
    r = httpx.post(
        f"{url}/api/v1/connections/sync",
        json={"connectionId": connection_id},
        timeout=300,
    )
    r.raise_for_status()

    # Airbyte writes to a destination; we read from the configured output path
    # For the hybrid approach, Airbyte should write to a local filesystem destination
    # that maps to our filestore directory
    logger.info(f"Airbyte sync triggered for connection {connection_id}")
    return []  # Airbyte writes directly to destination; files picked up by filestore scan
