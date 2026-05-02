"""
Data Connectors — Enterprise data ingestion framework.

Supports built-in connectors (databases, cloud storage, APIs, drives)
and optional Airbyte sidecar for 300+ exotic sources.

Pipeline: Source → Pull → Filestore (staging) → Index to ChromaDB
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectorType(str, Enum):
    DATABASE = "database"
    CLOUD_STORAGE = "cloud_storage"
    API = "api"
    GOOGLE_DRIVE = "google_drive"
    SHAREPOINT = "sharepoint"
    AIRBYTE = "airbyte"


class SyncStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


CONNECTOR_CATALOG = {
    "database": {
        "name": "Database",
        "description": "Pull data from SQL databases (PostgreSQL, MySQL, SQL Server)",
        "icon": "database",
        "config_schema": {
            "db_type": {"type": "select", "options": ["postgresql", "mysql", "mssql"], "required": True},
            "host": {"type": "string", "required": True},
            "port": {"type": "number", "required": True},
            "database": {"type": "string", "required": True},
            "username": {"type": "string", "required": True},
            "password": {"type": "password", "required": True},
            "query": {"type": "textarea", "placeholder": "SELECT * FROM documents", "required": True},
            "text_columns": {"type": "string", "placeholder": "content,title", "required": True},
        },
    },
    "cloud_storage": {
        "name": "Cloud Storage",
        "description": "Import files from S3, Azure Blob, or Google Cloud Storage",
        "icon": "cloud",
        "config_schema": {
            "provider": {"type": "select", "options": ["s3", "azure_blob", "gcs"], "required": True},
            "bucket": {"type": "string", "required": True},
            "prefix": {"type": "string", "placeholder": "documents/", "required": False},
            "file_extensions": {"type": "string", "placeholder": ".pdf,.txt,.md,.docx", "required": False},
            "access_key": {"type": "password", "required": False, "description": "For S3/GCS"},
            "secret_key": {"type": "password", "required": False},
            "connection_string": {"type": "password", "required": False, "description": "For Azure Blob"},
        },
    },
    "api": {
        "name": "REST API",
        "description": "Pull data from any REST API endpoint",
        "icon": "api",
        "config_schema": {
            "url": {"type": "string", "required": True, "placeholder": "https://api.example.com/data"},
            "method": {"type": "select", "options": ["GET", "POST"], "required": True},
            "headers": {"type": "textarea", "placeholder": '{"Authorization": "Bearer ..."}', "required": False},
            "body": {"type": "textarea", "required": False},
            "response_path": {"type": "string", "placeholder": "data.items", "required": False},
            "text_field": {"type": "string", "placeholder": "content", "required": True},
            "name_field": {"type": "string", "placeholder": "title", "required": False},
        },
    },
    "google_drive": {
        "name": "Google Drive",
        "description": "Import documents from Google Drive folders",
        "icon": "drive",
        "config_schema": {
            "credentials_json": {"type": "textarea", "required": True, "description": "Service account JSON"},
            "folder_id": {"type": "string", "required": True, "placeholder": "Drive folder ID"},
            "file_types": {"type": "string", "placeholder": "document,spreadsheet,pdf", "required": False},
        },
    },
    "sharepoint": {
        "name": "SharePoint",
        "description": "Import documents from SharePoint sites",
        "icon": "sharepoint",
        "config_schema": {
            "site_url": {"type": "string", "required": True, "placeholder": "https://company.sharepoint.com/sites/team"},
            "client_id": {"type": "string", "required": True},
            "client_secret": {"type": "password", "required": True},
            "tenant_id": {"type": "string", "required": True},
            "library": {"type": "string", "placeholder": "Shared Documents", "required": False},
        },
    },
    "airbyte": {
        "name": "Airbyte (300+ Sources)",
        "description": "Use Airbyte OSS for advanced/exotic data sources",
        "icon": "airbyte",
        "config_schema": {
            "airbyte_url": {"type": "string", "required": True, "placeholder": "http://airbyte:8000"},
            "connection_id": {"type": "string", "required": True, "placeholder": "Airbyte connection UUID"},
        },
    },
}


def generate_connector_id() -> str:
    return f"conn_{uuid.uuid4().hex[:12]}"


def generate_job_id() -> str:
    return f"job_{uuid.uuid4().hex[:12]}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
